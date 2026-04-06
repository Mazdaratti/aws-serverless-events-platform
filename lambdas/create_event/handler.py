import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # Keep the handler small and linear:
    # 1. resolve authenticated caller context
    # 2. parse and validate the request payload
    # 3. build the canonical DynamoDB item
    # 4. write it
    # 5. return an API Gateway-style response
    logger.info("create-event invocation started")

    try:
        caller_context = _get_caller_context(event)
        payload = _extract_payload(event)
        validated_payload = _validate_payload(payload=payload, caller_context=caller_context)

        events_table_name = _get_required_env("EVENTS_TABLE_NAME")
        table = _get_dynamodb_table(events_table_name)

        event_uuid = str(uuid.uuid4())
        event_pk = f"EVENT#{event_uuid}"

        normalized_event_date = _normalize_event_date(validated_payload["date"])
        created_at = _utc_now_iso8601()

        item = _build_event_item(
            event_uuid=event_uuid,
            event_pk=event_pk,
            normalized_event_date=normalized_event_date,
            created_at=created_at,
            payload=validated_payload,
        )

        logger.info("writing event item %s to DynamoDB", event_pk)
        table.put_item(Item=item)
        logger.info("event item %s written successfully", event_pk)

        return _success_response(
            status_code=201,
            body={"item": _to_public_event_dto(item)},
        )
    except ValueError as exc:
        logger.info("create-event validation failed: %s", exc)
        return _error_response(status_code=400, message=str(exc))
    except Exception:
        logger.exception("create-event failed unexpectedly")
        return _error_response(status_code=500, message="Internal server error.")


def _extract_payload(event: dict[str, Any]) -> dict[str, Any]:
    # Support both direct Lambda invocation and the future API Gateway event
    # shape where the request body is delivered separately.
    if "body" not in event:
        if isinstance(event, dict):
            return event
        raise ValueError("Event payload must be a JSON object.")

    body = event["body"]

    if isinstance(body, dict):
        return body

    if isinstance(body, str):
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must contain valid JSON.") from exc

        if not isinstance(payload, dict):
            raise ValueError("Request body JSON must be an object.")

        return payload

    raise ValueError("Request body must be a JSON object or JSON string.")


def _validate_payload(*, payload: dict[str, Any], caller_context: dict[str, Any]) -> dict[str, Any]:
    # Validate the minimum event contract first, then apply business rules such
    # as ownership and admin-only creation.
    title = str(payload.get("title", "")).strip()
    if not title:
        raise ValueError("title is required and must not be empty.")

    if "date" not in payload:
        raise ValueError("date is required.")

    description = str(payload.get("description", "")).strip()
    location = str(payload.get("location", "")).strip()

    capacity = payload.get("capacity")
    if capacity is not None:
        if not isinstance(capacity, int) or isinstance(capacity, bool):
            raise ValueError("capacity must be an integer when provided.")
        if capacity < 0:
            raise ValueError("capacity must be zero or greater when provided.")

    is_public = _coerce_bool(payload.get("is_public", True), "is_public")
    requires_admin = _coerce_bool(payload.get("requires_admin", False), "requires_admin")

    # Admin-only events require an admin caller. This stays business logic in
    # Lambda even though generic auth is handled elsewhere.
    if requires_admin and not caller_context["is_admin"]:
        raise ValueError("admin privileges are required to create admin-only events.")

    return {
        "title": title,
        "date": payload["date"],
        "description": description,
        "location": location,
        "capacity": capacity,
        "is_public": is_public,
        "requires_admin": requires_admin,
        # Ownership comes from authenticated caller context, never from a
        # request-body field that a client could spoof.
        "creator_id": caller_context["user_id"],
    }


def _build_event_item(
    *,
    event_uuid: str,
    event_pk: str,
    normalized_event_date: str,
    created_at: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    # This is the canonical event record shape currently expected by the
    # platform's DynamoDB design.
    item = {
        "event_pk": event_pk,
        # Canonical event records must always carry explicit lifecycle state so
        # later handlers never need to infer whether an event is active.
        "status": "ACTIVE",
        "title": payload["title"],
        "date": normalized_event_date,
        "description": payload["description"],
        "location": payload["location"],
        "capacity": payload["capacity"],
        "is_public": payload["is_public"],
        "requires_admin": payload["requires_admin"],
        "creator_id": payload["creator_id"],
        "created_at": created_at,
        "rsvp_total": 0,
        "attending_count": 0,
        "not_attending_count": 0,
        "creator_events_gsi_pk": f"CREATOR#{payload['creator_id']}",
        "creator_events_gsi_sk": f"{normalized_event_date}#{event_uuid}",
    }

    # Public listing stays sparse: only public events receive the public GSI
    # attributes so private records are omitted from that index entirely.
    if payload["is_public"]:
        item["public_upcoming_gsi_pk"] = "PUBLIC"
        item["public_upcoming_gsi_sk"] = f"{normalized_event_date}#{event_uuid}"

    return item


def _to_public_event_dto(item: dict[str, Any]) -> dict[str, Any]:
    # Map the canonical newly created event record into the locked public
    # event DTO used across event handlers.
    event_id = item["event_pk"].removeprefix("EVENT#")

    return {
        "event_id": event_id,
        "status": item["status"],
        "title": item["title"],
        "date": item["date"],
        "description": item["description"],
        "location": item["location"],
        "capacity": item["capacity"],
        "is_public": item["is_public"],
        "requires_admin": item["requires_admin"],
        "created_by": item["creator_id"],
        "created_at": item["created_at"],
        "rsvp_count": item["rsvp_total"],
        "attending_count": item["attending_count"],
    }


def _normalize_event_date(raw_value: Any) -> str:
    # Normalize all accepted date inputs into one stored format so DynamoDB
    # items and index sort keys stay consistent.
    if not isinstance(raw_value, str):
        raise ValueError("date must be a string.")

    candidate = raw_value.strip()
    if not candidate:
        raise ValueError("date must not be empty.")

    # Accept plain dates for convenience and normalize them to midnight UTC.
    if len(candidate) == 10:
        try:
            parsed_date = datetime.strptime(candidate, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("date must use ISO 8601 format.") from exc

        return parsed_date.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

    try:
        parsed_datetime = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("date must use ISO 8601 format.") from exc

    if parsed_datetime.tzinfo is None:
        parsed_datetime = parsed_datetime.replace(tzinfo=timezone.utc)
    else:
        parsed_datetime = parsed_datetime.astimezone(timezone.utc)

    return parsed_datetime.isoformat().replace("+00:00", "Z")


def _utc_now_iso8601() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _get_required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} environment variable is required.")
    return value


def _get_caller_context(event: dict[str, Any]) -> dict[str, Any]:
    # Keep the temporary direct-invoke/test event shape aligned with the future
    # API Gateway handoff: requestContext.authorizer carries caller identity.
    request_context = event.get("requestContext", {})
    if not isinstance(request_context, dict):
        raise ValueError("Authenticated caller context is required.")

    authorizer = request_context.get("authorizer", {})
    if not isinstance(authorizer, dict):
        raise ValueError("Authenticated caller context is required.")

    user_id = str(authorizer.get("user_id", "")).strip()
    if not user_id:
        raise ValueError("Authenticated caller context is required.")

    return {
        "user_id": user_id,
        "is_admin": _coerce_optional_bool(
            authorizer.get("is_admin", False),
            "requestContext.authorizer.is_admin",
        ),
    }


def _get_dynamodb_table(table_name: str):
    # Create the DynamoDB table resource lazily so importing this module does
    # not require ambient AWS region configuration during tests.
    return boto3.resource("dynamodb").Table(table_name)


def _coerce_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value

    raise ValueError(f"{field_name} must be a boolean when provided.")


def _coerce_optional_bool(value: Any, field_name: str) -> bool:
    # Some authorizer fields may be omitted in early direct invocation/testing
    # flows, so treat missing optional booleans as False.
    if value is None:
        return False

    return _coerce_bool(value, field_name)


def _success_response(*, status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    # Keep the response shape aligned with the future API Gateway integration
    # even though the function can already be invoked directly today.
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _error_response(*, status_code: int, message: str) -> dict[str, Any]:
    return _success_response(
        status_code=status_code,
        body={"message": message},
    )
