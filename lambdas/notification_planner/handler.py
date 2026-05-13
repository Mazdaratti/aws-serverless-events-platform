import json
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger()
logger.setLevel(logging.INFO)


SUPPORTED_DETAIL_TYPES = {"event.updated", "event.cancelled"}


class NotificationPlannerError(Exception):
    """Raised when one supported notification planning message cannot be processed."""


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, list[dict[str, str]]]:
    """Plan recipient-level participant email jobs from SQS-dispatched event messages."""
    del context

    records = _resolve_sqs_records(event)
    dynamodb_client = _get_dynamodb_client()
    sqs_client = _get_sqs_client()

    batch_item_failures: list[dict[str, str]] = []

    logger.info("notification-planner invocation started with %s SQS records", len(records))

    for record in records:
        message_id = _resolve_message_id(record)

        try:
            _process_record(
                record=record,
                dynamodb_client=dynamodb_client,
                sqs_client=sqs_client,
            )
        except Exception:
            logger.exception("notification-planner failed to process SQS message %s", message_id)
            batch_item_failures.append({"itemIdentifier": message_id})

    logger.info(
        "notification-planner completed with %s failed SQS records",
        len(batch_item_failures),
    )
    return {"batchItemFailures": batch_item_failures}


def _process_record(*, record: dict[str, Any], dynamodb_client: Any, sqs_client: Any) -> None:
    """Process one SQS record and enqueue recipient-level email jobs when supported."""
    eventbridge_event = _parse_eventbridge_event(record)
    detail_type = _resolve_detail_type(eventbridge_event)

    if detail_type not in SUPPORTED_DETAIL_TYPES:
        logger.info("notification-planner ignored unsupported detail-type %s", detail_type)
        return

    detail = _resolve_detail(eventbridge_event)
    planner_message = _build_planner_message(detail_type=detail_type, detail=detail)

    recipient_user_ids = _query_authenticated_rsvp_user_ids(
        dynamodb_client=dynamodb_client,
        event_id=planner_message["event_id"],
    )

    logger.info(
        "notification-planner found %s authenticated RSVP recipients for event %s",
        len(recipient_user_ids),
        planner_message["event_id"],
    )

    for recipient_user_id in recipient_user_ids:
        _send_recipient_message(
            sqs_client=sqs_client,
            message={
                **planner_message,
                "recipient_user_id": recipient_user_id,
            },
        )


def _resolve_sqs_records(event: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(event, dict):
        raise NotificationPlannerError("SQS event must be a JSON object.")

    records = event.get("Records")
    if not isinstance(records, list):
        raise NotificationPlannerError("SQS event Records must be a list.")

    resolved_records: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            raise NotificationPlannerError("Each SQS record must be a JSON object.")
        resolved_records.append(record)

    return resolved_records


def _resolve_message_id(record: dict[str, Any]) -> str:
    message_id = record.get("messageId")
    if not isinstance(message_id, str) or not message_id.strip():
        raise NotificationPlannerError("SQS record messageId must be a non-empty string.")
    return message_id


def _parse_eventbridge_event(record: dict[str, Any]) -> dict[str, Any]:
    body = record.get("body")
    if not isinstance(body, str) or not body.strip():
        raise NotificationPlannerError("SQS record body must be a non-empty JSON string.")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise NotificationPlannerError("SQS record body must contain valid JSON.") from exc

    if not isinstance(payload, dict):
        raise NotificationPlannerError("SQS record body must decode to a JSON object.")

    return payload


def _resolve_detail_type(eventbridge_event: dict[str, Any]) -> str:
    detail_type = eventbridge_event.get("detail-type")
    if not isinstance(detail_type, str) or not detail_type.strip():
        raise NotificationPlannerError("EventBridge detail-type must be a non-empty string.")
    return detail_type.strip()


def _resolve_detail(eventbridge_event: dict[str, Any]) -> dict[str, Any]:
    detail = eventbridge_event.get("detail")
    if not isinstance(detail, dict):
        raise NotificationPlannerError("EventBridge detail must be a JSON object.")
    return detail


def _build_planner_message(*, detail_type: str, detail: dict[str, Any]) -> dict[str, Any]:
    message: dict[str, Any] = {
        "notification_type": detail_type,
        "event_id": _required_detail_string(detail, "event_id"),
        "event_title": _required_detail_string(detail, "title"),
        "event_detail_path": _required_detail_string(detail, "event_detail_path"),
        "occurred_at": _required_detail_string(detail, "occurred_at"),
    }

    if detail_type == "event.updated":
        message["changed_fields"] = _required_changed_fields(detail)

    return message


def _required_detail_string(detail: dict[str, Any], field_name: str) -> str:
    value = detail.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise NotificationPlannerError(f"EventBridge detail.{field_name} must be a non-empty string.")
    return value.strip()


def _required_changed_fields(detail: dict[str, Any]) -> list[str]:
    value = detail.get("changed_fields")
    if not isinstance(value, list):
        raise NotificationPlannerError("EventBridge detail.changed_fields must be a list for event.updated.")

    changed_fields: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise NotificationPlannerError("EventBridge detail.changed_fields must contain only non-empty strings.")
        changed_fields.append(item.strip())

    return changed_fields


def _query_authenticated_rsvp_user_ids(*, dynamodb_client: Any, event_id: str) -> list[str]:
    rsvps_table_name = _get_required_env("RSVPS_TABLE_NAME")
    query_kwargs: dict[str, Any] = {
        "TableName": rsvps_table_name,
        "KeyConditionExpression": "event_pk = :event_pk",
        "ExpressionAttributeValues": {
            ":event_pk": {"S": f"EVENT#{event_id}"},
        },
        "ScanIndexForward": True,
    }

    recipient_user_ids: list[str] = []

    while True:
        try:
            response = dynamodb_client.query(**query_kwargs)
        except ClientError as exc:
            raise NotificationPlannerError("Failed to query RSVP recipients.") from exc

        raw_items = response.get("Items", [])
        if not isinstance(raw_items, list):
            raise NotificationPlannerError("DynamoDB RSVP query Items must be a list.")

        for item in raw_items:
            if not isinstance(item, dict):
                raise NotificationPlannerError("Each DynamoDB RSVP item must be an object.")

            recipient_user_id = _extract_authenticated_rsvp_user_id(item)
            if recipient_user_id is not None:
                recipient_user_ids.append(recipient_user_id)

        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            return recipient_user_ids
        if not isinstance(last_evaluated_key, dict):
            raise NotificationPlannerError("DynamoDB LastEvaluatedKey must be an object when present.")

        query_kwargs["ExclusiveStartKey"] = last_evaluated_key


def _extract_authenticated_rsvp_user_id(item: dict[str, Any]) -> str | None:
    subject_type = _deserialize_optional_string(item.get("subject_type"), field_name="subject_type")

    if subject_type == "ANON":
        return None
    if subject_type != "USER":
        return None

    # Both attending=true and attending=false authenticated RSVP users are
    # notified. The value is validated for record integrity but not filtered.
    attending = item.get("attending")
    if not isinstance(attending, dict) or not isinstance(attending.get("BOOL"), bool):
        raise NotificationPlannerError("Stored USER RSVP attending must be a DynamoDB boolean attribute.")

    user_id = _deserialize_optional_string(item.get("user_id"), field_name="user_id")
    if user_id is None:
        raise NotificationPlannerError("Stored USER RSVP items must include user_id.")

    return user_id


def _deserialize_optional_string(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, dict) or value.get("S") is None:
        raise NotificationPlannerError(f"Stored RSVP {field_name} must be a DynamoDB string attribute when present.")

    text = value["S"]
    if not isinstance(text, str):
        raise NotificationPlannerError(f"Stored RSVP {field_name} must be a string when present.")

    candidate = text.strip()
    if not candidate:
        return None
    return candidate


def _send_recipient_message(*, sqs_client: Any, message: dict[str, Any]) -> None:
    queue_url = _get_required_env("NOTIFICATION_EMAIL_QUEUE_URL")
    try:
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message, separators=(",", ":"), sort_keys=True),
        )
    except ClientError as exc:
        raise NotificationPlannerError("Failed to enqueue recipient email job.") from exc


def _get_required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _get_dynamodb_client() -> Any:
    return boto3.client("dynamodb")


def _get_sqs_client() -> Any:
    return boto3.client("sqs")
