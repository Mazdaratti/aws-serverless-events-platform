import json
import logging
import os
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class EventDtoMappingError(Exception):
    """Raised when a stored DynamoDB event item does not match the locked DTO contract."""


class ConditionalCancelStateError(Exception):
    """Raised when a conditional cancel fails for an unexpected internal reason."""


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # Keep the handler flow small and predictable:
    #
    # 1. validate the top-level event shape
    # 2. resolve caller context and event identifier
    # 3. read the current event item
    # 4. enforce existence, authorization, and lifecycle rules
    # 5. issue a conditional DynamoDB UpdateItem when the event is still active
    # 6. return the current public event DTO in the standard wrapper
    logger.info("cancel-event invocation started")

    try:
        if not isinstance(event, dict):
            raise ValueError("Event payload must be a JSON object.")

        caller_context = _get_caller_context(event)
        event_id = _validate_event_id(event)

        events_table_name = _get_required_env("EVENTS_TABLE_NAME")
        table = _get_dynamodb_table(events_table_name)

        response_body = _cancel_event(
            table=table,
            event_id=event_id,
            caller_context=caller_context,
        )
        logger.info("cancel-event completed for event_id %s", event_id)

        return _success_response(status_code=200, body=response_body)
    except ValueError as exc:
        logger.info("cancel-event validation failed: %s", exc)
        return _error_response(status_code=400, message=str(exc))
    except PermissionError as exc:
        logger.info("cancel-event authorization failed: %s", exc)
        return _error_response(status_code=403, message=str(exc))
    except LookupError as exc:
        logger.info("cancel-event not found: %s", exc)
        return _error_response(status_code=404, message=str(exc))
    except EventDtoMappingError:
        logger.exception("cancel-event encountered an invalid stored event shape")
        return _error_response(status_code=500, message="Internal server error.")
    except ConditionalCancelStateError:
        logger.exception("cancel-event conditional write failed for an unexpected internal state")
        return _error_response(status_code=500, message="Internal server error.")
    except Exception:
        logger.exception("cancel-event failed unexpectedly")
        return _error_response(status_code=500, message="Internal server error.")


def _get_caller_context(event: dict[str, Any]) -> dict[str, Any]:
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


def _validate_event_id(event: dict[str, Any]) -> str:
    raw_event_id = _resolve_event_id(event)

    if raw_event_id is None:
        raise ValueError("event_id is required.")

    if not isinstance(raw_event_id, str):
        raise ValueError("event_id must be a non-empty string.")

    event_id = raw_event_id.strip()
    if not event_id:
        raise ValueError("event_id must be a non-empty string.")

    if event_id.startswith("EVENT#"):
        raise ValueError("event_id must use the public identifier, not the internal storage key.")

    return event_id


def _resolve_event_id(event: dict[str, Any]) -> Any:
    path_parameters = event.get("pathParameters")
    if path_parameters is not None:
        if not isinstance(path_parameters, dict):
            raise ValueError("pathParameters must be an object when provided.")

        if "event_id" in path_parameters:
            return path_parameters.get("event_id")

    return event.get("event_id")


def _cancel_event(*, table: Any, event_id: str, caller_context: dict[str, Any]) -> dict[str, Any]:
    event_pk = f"EVENT#{event_id}"
    logger.info("reading current event item %s from DynamoDB", event_pk)
    current_response = table.get_item(Key={"event_pk": event_pk})

    current_item = current_response.get("Item")
    if current_item is None:
        raise LookupError("Event not found.")

    if not isinstance(current_item, dict):
        raise EventDtoMappingError("Stored DynamoDB item must be an object.")

    current_state = _to_internal_event_state(current_item)
    _authorize_cancel(caller_context=caller_context, current_state=current_state)

    if current_state["status"] == "CANCELLED":
        return {"item": _to_event_dto(current_item)}

    logger.info("cancelling event item %s in DynamoDB", event_pk)
    try:
        update_response = table.update_item(
            Key={"event_pk": event_pk},
            UpdateExpression="SET #status = :cancelled REMOVE public_upcoming_gsi_pk, public_upcoming_gsi_sk",
            ExpressionAttributeNames={
                "#status": "status",
            },
            ExpressionAttributeValues={
                ":active": "ACTIVE",
                ":cancelled": "CANCELLED",
            },
            ConditionExpression="attribute_exists(event_pk) AND #status = :active",
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            raise

        return _handle_conditional_cancel_failure(
            table=table,
            event_id=event_id,
            caller_context=caller_context,
        )

    updated_item = update_response.get("Attributes")
    if not isinstance(updated_item, dict):
        raise EventDtoMappingError("Updated DynamoDB item must be an object.")

    return {"item": _to_event_dto(updated_item)}


def _handle_conditional_cancel_failure(
    *,
    table: Any,
    event_id: str,
    caller_context: dict[str, Any],
) -> dict[str, Any]:
    event_pk = f"EVENT#{event_id}"
    latest_response = table.get_item(Key={"event_pk": event_pk})
    latest_item = latest_response.get("Item")

    if latest_item is None:
        raise LookupError("Event not found.")

    if not isinstance(latest_item, dict):
        raise EventDtoMappingError("Stored DynamoDB item must be an object.")

    latest_state = _to_internal_event_state(latest_item)
    _authorize_cancel(caller_context=caller_context, current_state=latest_state)

    if latest_state["status"] == "CANCELLED":
        return {"item": _to_event_dto(latest_item)}

    raise ConditionalCancelStateError(
        "Conditional cancel failed for an unexpected internal state transition."
    )


def _to_internal_event_state(item: dict[str, Any]) -> dict[str, Any]:
    """Read the storage-facing event state needed for cancel authorization and lifecycle checks."""
    return {
        "event_id": _to_event_id(item.get("event_pk")),
        "status": _normalize_status(item.get("status")),
        "creator_id": _normalize_required_text(item.get("creator_id"), field_name="creator_id"),
    }


def _authorize_cancel(*, caller_context: dict[str, Any], current_state: dict[str, Any]) -> None:
    """Authorize creator/admin cancel access for the current event."""
    if caller_context["is_admin"]:
        return

    if caller_context["user_id"] == current_state["creator_id"]:
        return

    raise PermissionError("You are not allowed to cancel this event.")


def _to_event_dto(item: dict[str, Any]) -> dict[str, Any]:
    """Map a canonical event record into the locked public event DTO."""
    return {
        "event_id": _to_event_id(item.get("event_pk")),
        "status": _normalize_status(item.get("status")),
        "title": _normalize_text(item.get("title"), field_name="title"),
        "date": _normalize_text(item.get("date"), field_name="date"),
        "description": _normalize_text(item.get("description"), field_name="description"),
        "location": _normalize_text(item.get("location"), field_name="location"),
        "capacity": _normalize_capacity(item.get("capacity")),
        "is_public": _normalize_bool(item.get("is_public"), field_name="is_public"),
        "requires_admin": _normalize_bool(item.get("requires_admin"), field_name="requires_admin"),
        "created_by": _normalize_required_text(item.get("creator_id"), field_name="creator_id"),
        "created_at": _normalize_text(item.get("created_at"), field_name="created_at"),
        "rsvp_count": _normalize_counter(item.get("rsvp_total"), field_name="rsvp_total"),
        "attending_count": _normalize_counter(item.get("attending_count"), field_name="attending_count"),
    }


def _to_event_id(raw_event_pk: Any) -> str:
    if not isinstance(raw_event_pk, str):
        raise EventDtoMappingError("Stored event_pk must be a string.")

    event_pk = raw_event_pk.strip()
    if not event_pk:
        raise EventDtoMappingError("Stored event_pk must not be empty.")

    if not event_pk.startswith("EVENT#"):
        raise EventDtoMappingError("Stored event_pk must use the EVENT# prefix.")

    event_id = event_pk.removeprefix("EVENT#")
    if not event_id:
        raise EventDtoMappingError("Stored event_pk must contain a public identifier.")

    return event_id


def _normalize_text(value: Any, *, field_name: str) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    raise EventDtoMappingError(f"Stored {field_name} must be a string or null.")


def _normalize_required_text(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise EventDtoMappingError(f"Stored {field_name} must be a string.")

    candidate = value.strip()
    if not candidate:
        raise EventDtoMappingError(f"Stored {field_name} must not be empty.")

    return candidate


def _normalize_capacity(value: Any) -> int | None:
    if value is None:
        return None

    if isinstance(value, bool):
        raise EventDtoMappingError("Stored capacity must be an integer or null.")

    if isinstance(value, int):
        return value

    if isinstance(value, Decimal):
        if value % 1 != 0:
            raise EventDtoMappingError("Stored capacity must be an integer or null.")

        return int(value)

    raise EventDtoMappingError("Stored capacity must be an integer or null.")


def _normalize_bool(value: Any, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value

    raise EventDtoMappingError(f"Stored {field_name} must be a boolean.")


def _normalize_status(value: Any) -> str:
    """Validate and normalize the stored lifecycle status for cancel-event."""
    if value == "ACTIVE":
        return "ACTIVE"

    if value == "CANCELLED":
        return "CANCELLED"

    raise EventDtoMappingError("Stored status must be ACTIVE or CANCELLED.")


def _normalize_counter(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool):
        raise EventDtoMappingError(f"Stored {field_name} must be an integer.")

    if isinstance(value, int):
        return value

    if isinstance(value, Decimal):
        if value % 1 != 0:
            raise EventDtoMappingError(f"Stored {field_name} must be an integer.")

        return int(value)

    raise EventDtoMappingError(f"Stored {field_name} must be an integer.")


def _get_required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} environment variable is required.")
    return value


def _get_dynamodb_table(table_name: str):
    return boto3.resource("dynamodb").Table(table_name)


def _coerce_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value

    raise ValueError(f"{field_name} must be a boolean when provided.")


def _coerce_optional_bool(value: Any, field_name: str) -> bool:
    if value is None:
        return False

    return _coerce_bool(value, field_name)


def _success_response(*, status_code: int, body: dict[str, Any]) -> dict[str, Any]:
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
