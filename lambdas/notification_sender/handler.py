import html
import json
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger()
logger.setLevel(logging.INFO)


SUPPORTED_NOTIFICATION_TYPES = {"event.updated", "event.cancelled"}


class NotificationSenderError(Exception):
    """Raised when one recipient-level participant email job cannot be sent."""


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, list[dict[str, str]]]:
    # Keep the sender batch flow partial-batch friendly:
    #
    # 1. validate the top-level SQS event shape
    # 2. process each recipient-level job independently
    # 3. resolve the current recipient email from Cognito at send time
    # 4. render by choosing a stable SES template and safe template data
    # 5. collect only failed SQS message IDs
    # 6. return the AWS Lambda partial batch response contract
    del context

    records = _resolve_sqs_records(event)
    cognito_client = _get_cognito_client()
    ses_client = _get_ses_client()

    batch_item_failures: list[dict[str, str]] = []

    logger.info("notification-sender invocation started with %s SQS records", len(records))

    for record in records:
        message_id = _resolve_message_id(record)

        try:
            _process_record(
                record=record,
                cognito_client=cognito_client,
                ses_client=ses_client,
            )
        except Exception:
            logger.exception("notification-sender failed to process SQS message %s", message_id)
            batch_item_failures.append({"itemIdentifier": message_id})

    logger.info(
        "notification-sender completed with %s failed SQS records",
        len(batch_item_failures),
    )
    return {"batchItemFailures": batch_item_failures}


def _process_record(*, record: dict[str, Any], cognito_client: Any, ses_client: Any) -> None:
    """Process one recipient-level email job and send one templated email."""
    message = _parse_recipient_message(record)
    notification_type = _required_string(message, "notification_type")

    if notification_type not in SUPPORTED_NOTIFICATION_TYPES:
        raise NotificationSenderError(f"Unsupported notification_type: {notification_type}")

    # The queued job carries the stable platform identity only. The current
    # contact email is resolved from Cognito here, so queued messages never
    # become an email-address store.
    recipient_user_id = _required_string(message, "recipient_user_id")
    recipient_email = _resolve_recipient_email(
        cognito_client=cognito_client,
        recipient_user_id=recipient_user_id,
    )
    _validate_email_address(recipient_email)

    template_name = _resolve_template_name(notification_type)
    template_data = _build_template_data(notification_type=notification_type, message=message)

    _send_templated_email(
        ses_client=ses_client,
        recipient_email=recipient_email,
        template_name=template_name,
        template_data=template_data,
    )


def _resolve_sqs_records(event: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate the Lambda SQS batch envelope and return its records."""
    if not isinstance(event, dict):
        raise NotificationSenderError("SQS event must be a JSON object.")

    records = event.get("Records")
    if not isinstance(records, list):
        raise NotificationSenderError("SQS event Records must be a list.")

    resolved_records: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            raise NotificationSenderError("Each SQS record must be a JSON object.")
        resolved_records.append(record)

    return resolved_records


def _resolve_message_id(record: dict[str, Any]) -> str:
    """Return the SQS message ID used by Lambda partial batch responses."""
    message_id = record.get("messageId")
    if not isinstance(message_id, str) or not message_id.strip():
        raise NotificationSenderError("SQS record messageId must be a non-empty string.")
    return message_id


def _parse_recipient_message(record: dict[str, Any]) -> dict[str, Any]:
    """Decode one recipient-level email job from an SQS message body."""
    body = record.get("body")
    if not isinstance(body, str) or not body.strip():
        raise NotificationSenderError("SQS record body must be a non-empty JSON string.")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise NotificationSenderError("SQS record body must contain valid JSON.") from exc

    if not isinstance(payload, dict):
        raise NotificationSenderError("SQS record body must decode to a JSON object.")

    return payload


def _resolve_recipient_email(*, cognito_client: Any, recipient_user_id: str) -> str:
    """Resolve the current recipient email from Cognito using canonical sub."""
    _validate_cognito_sub(recipient_user_id)

    try:
        response = cognito_client.list_users(
            UserPoolId=_get_required_env("COGNITO_USER_POOL_ID"),
            Filter=f'sub = "{recipient_user_id}"',
            Limit=2,
        )
    except ClientError as exc:
        raise NotificationSenderError("Failed to resolve recipient email from Cognito.") from exc

    users = response.get("Users", [])
    if not isinstance(users, list):
        raise NotificationSenderError("Cognito ListUsers response Users must be a list.")
    if len(users) != 1:
        raise NotificationSenderError("Cognito sub lookup must return exactly one user.")

    return _extract_email_attribute(users[0])


def _validate_cognito_sub(recipient_user_id: str) -> None:
    # The Cognito ListUsers filter is a small expression string. Keep the
    # canonical sub value simple so the sender cannot accidentally build an
    # invalid or broadened filter.
    if '"' in recipient_user_id or "\\" in recipient_user_id:
        raise NotificationSenderError("recipient_user_id contains characters that are not valid for a Cognito filter.")


def _extract_email_attribute(user: Any) -> str:
    if not isinstance(user, dict):
        raise NotificationSenderError("Cognito user must be a JSON object.")

    attributes = user.get("Attributes", [])
    if not isinstance(attributes, list):
        raise NotificationSenderError("Cognito user Attributes must be a list.")

    for attribute in attributes:
        if not isinstance(attribute, dict):
            raise NotificationSenderError("Each Cognito user attribute must be a JSON object.")
        if attribute.get("Name") == "email":
            value = attribute.get("Value")
            if isinstance(value, str) and value.strip():
                return value.strip()

    raise NotificationSenderError("Cognito user must have a current email attribute.")


def _validate_email_address(email_address: str) -> None:
    if not email_address or email_address.strip() != email_address:
        raise NotificationSenderError("Recipient email must not be empty or contain surrounding whitespace.")
    if "@" not in email_address or any(character.isspace() for character in email_address):
        raise NotificationSenderError("Recipient email must be an email-like address.")


def _resolve_template_name(notification_type: str) -> str:
    if notification_type == "event.updated":
        return _get_required_env("SES_TEMPLATE_EVENT_UPDATED")
    if notification_type == "event.cancelled":
        return _get_required_env("SES_TEMPLATE_EVENT_CANCELLED")
    raise NotificationSenderError(f"Unsupported notification_type: {notification_type}")


def _build_template_data(*, notification_type: str, message: dict[str, Any]) -> dict[str, Any]:
    """Build SES template data from safe user-facing message fields."""
    event_title = _required_string(message, "event_title")
    event_detail_path = _required_event_detail_path(message)

    # SES templates render the same data into text and HTML bodies. Values that
    # appear as visible HTML text are escaped before handoff. The event URL is
    # validated and composed separately because URL safety is a validation
    # concern, not a text-escaping concern.
    template_data: dict[str, Any] = {
        "event_title": _escape_template_value(event_title),
        "event_url": _build_event_url(event_detail_path),
    }

    if notification_type == "event.updated":
        template_data["changed_fields"] = [
            _escape_template_value(changed_field)
            for changed_field in _required_changed_fields(message)
        ]

    return template_data


def _required_event_detail_path(message: dict[str, Any]) -> str:
    value = _required_string(message, "event_detail_path")
    if not value.startswith("/app/events/"):
        raise NotificationSenderError("event_detail_path must start with /app/events/.")
    if any(character.isspace() for character in value) or any(
        character in value for character in ['"', "'", "\\", "<", ">"]
    ):
        raise NotificationSenderError("event_detail_path contains unsafe URL characters.")
    return value


def _build_event_url(event_detail_path: str) -> str:
    base_url = _get_required_env("FRONTEND_BASE_URL").rstrip("/")
    if not base_url.startswith("https://"):
        raise NotificationSenderError("FRONTEND_BASE_URL must start with https://.")
    return f"{base_url}{event_detail_path}"


def _required_changed_fields(message: dict[str, Any]) -> list[str]:
    value = message.get("changed_fields")
    if not isinstance(value, list):
        raise NotificationSenderError("changed_fields must be a list for event.updated.")

    changed_fields: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise NotificationSenderError("changed_fields must contain only non-empty strings.")
        changed_fields.append(item.strip())

    return changed_fields


def _send_templated_email(
    *,
    ses_client: Any,
    recipient_email: str,
    template_name: str,
    template_data: dict[str, Any],
) -> None:
    try:
        ses_client.send_templated_email(
            Source=_get_required_env("SES_SOURCE_EMAIL"),
            Destination={"ToAddresses": [recipient_email]},
            Template=template_name,
            TemplateData=json.dumps(template_data, separators=(",", ":"), sort_keys=True),
        )
    except ClientError as exc:
        raise NotificationSenderError("Failed to send participant notification email.") from exc


def _required_string(message: dict[str, Any], field_name: str) -> str:
    value = message.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise NotificationSenderError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _escape_template_value(value: str) -> str:
    return html.escape(value, quote=True)


def _get_required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _get_cognito_client() -> Any:
    return boto3.client("cognito-idp")


def _get_ses_client() -> Any:
    return boto3.client("ses")
