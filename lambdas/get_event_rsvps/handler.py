import base64
import json
import logging
import os
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError

from shared.auth import resolve_optional_caller


logger = logging.getLogger()
logger.setLevel(logging.INFO)


EVENT_NOT_FOUND_MESSAGE = "Event not found."
RSVP_READ_FORBIDDEN_MESSAGE = "You do not have permission to view RSVPs for this event."

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


class RequestValidationError(ValueError):
    """Raised when the incoming request shape or values are invalid."""


class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""


class EventStateError(Exception):
    """Raised when the stored event item has an invalid internal shape."""


class RsvpStateError(Exception):
    """Raised when the stored RSVP item has an invalid internal shape."""


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle creator/admin RSVP reads for one event."""
    del context

    # Keep the handler flow explicit and consistent with the existing Lambdas:
    #
    # 1. validate the top-level event shape
    # 2. resolve the request contract and caller context
    # 3. read the canonical event item
    # 4. authorize creator/admin access
    # 5. query one RSVP page for that event
    # 6. map storage items into the locked public response DTO
    # 7. return the standard API Gateway-style wrapper
    logger.info("get-event-rsvps invocation started")

    try:
        if not isinstance(event, dict):
            raise RequestValidationError("Event payload must be a JSON object.")

        request = _resolve_request(event)
        client = _get_dynamodb_client()

        response_body, status_code = _handle_get_event_rsvps(client=client, request=request)

        logger.info("get-event-rsvps completed for event_id %s", request["event_id"])
        return _success_response(status_code=status_code, body=response_body)
    except (RequestValidationError, ValueError) as exc:
        logger.info("get-event-rsvps validation failed: %s", exc)
        return _error_response(status_code=400, message=str(exc))
    except PermissionError as exc:
        logger.info("get-event-rsvps authorization failed: %s", exc)
        return _error_response(status_code=403, message=str(exc))
    except NotFoundError as exc:
        logger.info("get-event-rsvps event lookup failed: %s", exc)
        return _error_response(status_code=404, message=str(exc))
    except EventStateError:
        logger.exception("get-event-rsvps encountered an invalid stored event shape")
        return _error_response(status_code=500, message="Internal server error.")
    except RsvpStateError:
        logger.exception("get-event-rsvps encountered an invalid stored RSVP shape")
        return _error_response(status_code=500, message="Internal server error.")
    except ClientError:
        logger.exception("get-event-rsvps encountered an unexpected DynamoDB client failure")
        return _error_response(status_code=500, message="Internal server error.")
    except Exception:
        logger.exception("get-event-rsvps failed unexpectedly")
        return _error_response(status_code=500, message="Internal server error.")


def _handle_get_event_rsvps(*, client: Any, request: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Execute the locked RSVP read flow and return body plus HTTP status."""
    events_table_name = _get_required_env("EVENTS_TABLE_NAME")
    event_key = _build_event_key(request["event_id"])

    logger.info("reading current event item %s from DynamoDB", event_key["event_pk"]["S"])
    event_response = client.get_item(
        TableName=events_table_name,
        Key=event_key,
    )
    raw_event_item = event_response.get("Item")
    if raw_event_item is None:
        raise NotFoundError(EVENT_NOT_FOUND_MESSAGE)

    event = _deserialize_event_item(raw_event_item)
    _authorize_event_rsvp_read(
        event=event,
        caller_user_id=request["caller_context"]["user_id"],
        is_admin=request["caller_context"]["is_admin"],
    )

    query_result = _query_rsvps(
        client=client,
        event_id=request["event_id"],
        limit=request["limit"],
        next_cursor=request["next_cursor"],
    )

    return (
        {
            "event": _build_event_summary(event),
            "items": [_map_rsvp_item_to_dto(item) for item in query_result["items"]],
            "stats": _build_stats(event),
            "next_cursor": query_result["next_cursor"],
        },
        200,
    )


def _resolve_request(event: dict[str, Any]) -> dict[str, Any]:
    """Resolve the supported request shapes into one normalized contract."""
    event_id = _validate_event_id(_resolve_event_id(event))
    limit = _validate_limit(_resolve_limit(event))
    next_cursor = _decode_cursor(
        raw_value=_resolve_next_cursor(event),
        event_id=event_id,
    )
    # Resolve one normalized caller contract at the handler edge so the rest
    # of the business flow can stay focused on existence, authorization, and
    # RSVP read behavior instead of raw authorizer shapes.
    caller_context = resolve_optional_caller(event)

    return {
        "event_id": event_id,
        "limit": limit,
        "next_cursor": next_cursor,
        "caller_context": caller_context,
    }


def _resolve_event_id(event: dict[str, Any]) -> Any:
    """Resolve event_id from pathParameters first, then top-level payload."""
    path_parameters = event.get("pathParameters")
    if path_parameters is not None:
        if not isinstance(path_parameters, dict):
            raise RequestValidationError("pathParameters must be an object when provided.")

        if "event_id" in path_parameters:
            return path_parameters.get("event_id")

    return event.get("event_id")


def _validate_event_id(value: Any) -> str:
    """Validate that event_id is a trimmed public identifier string."""
    if value is None:
        raise RequestValidationError("event_id is required.")
    if not isinstance(value, str):
        raise RequestValidationError("event_id must be a non-empty string.")

    event_id = value.strip()
    if not event_id:
        raise RequestValidationError("event_id must be a non-empty string.")
    if event_id.startswith("EVENT#"):
        raise RequestValidationError("event_id must use the public identifier, not the internal storage key.")

    return event_id


def _resolve_limit(event: dict[str, Any]) -> Any:
    """Resolve limit from queryStringParameters first, then top-level input."""
    query_params = event.get("queryStringParameters")
    if query_params is not None:
        if not isinstance(query_params, dict):
            raise RequestValidationError("queryStringParameters must be an object when provided.")
        if "limit" in query_params:
            return query_params.get("limit")

    return event.get("limit")


def _validate_limit(value: Any) -> int:
    """Validate limit using the locked default and max bounds."""
    if value is None or value == "":
        return DEFAULT_LIMIT

    if isinstance(value, bool):
        raise RequestValidationError(f"limit must be an integer between 1 and {MAX_LIMIT}.")

    if isinstance(value, int):
        limit = value
    elif isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return DEFAULT_LIMIT

        try:
            limit = int(candidate)
        except ValueError as exc:
            raise RequestValidationError(f"limit must be an integer between 1 and {MAX_LIMIT}.") from exc
    else:
        raise RequestValidationError(f"limit must be an integer between 1 and {MAX_LIMIT}.")

    if limit < 1 or limit > MAX_LIMIT:
        raise RequestValidationError(f"limit must be an integer between 1 and {MAX_LIMIT}.")

    return limit


def _resolve_next_cursor(event: dict[str, Any]) -> Any:
    """Resolve next_cursor from queryStringParameters first, then top-level input."""
    query_params = event.get("queryStringParameters")
    if query_params is not None:
        if not isinstance(query_params, dict):
            raise RequestValidationError("queryStringParameters must be an object when provided.")
        if "next_cursor" in query_params:
            return query_params.get("next_cursor")

    return event.get("next_cursor")


def _decode_cursor(*, raw_value: Any, event_id: str) -> dict[str, Any] | None:
    """Decode opaque cursor into DynamoDB ExclusiveStartKey for this event."""
    if raw_value is None:
        return None

    if not isinstance(raw_value, str):
        raise RequestValidationError("next_cursor must be a valid opaque cursor.")

    candidate = raw_value.strip()
    if not candidate:
        return None

    padding = "=" * (-len(candidate) % 4)

    try:
        decoded_bytes = base64.urlsafe_b64decode(candidate + padding)
        decoded_payload = json.loads(decoded_bytes.decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise RequestValidationError("next_cursor must be a valid opaque cursor.") from exc

    if not isinstance(decoded_payload, dict):
        raise RequestValidationError("next_cursor must be a valid opaque cursor.")

    event_pk = decoded_payload.get("event_pk")
    subject_sk = decoded_payload.get("subject_sk")

    if not isinstance(event_pk, dict) or not isinstance(subject_sk, dict):
        raise RequestValidationError("next_cursor must be a valid opaque cursor.")

    if event_pk.get("S") != f"EVENT#{event_id}":
        raise RequestValidationError("next_cursor must belong to the requested event.")

    if not isinstance(subject_sk.get("S"), str) or not subject_sk["S"].strip():
        raise RequestValidationError("next_cursor must be a valid opaque cursor.")

    return decoded_payload


def _encode_cursor(last_evaluated_key: dict[str, Any] | None) -> str | None:
    """Encode DynamoDB LastEvaluatedKey into an opaque cursor."""
    if not last_evaluated_key:
        return None

    payload = json.dumps(last_evaluated_key, separators=(",", ":"), sort_keys=True)
    encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")
    return encoded.rstrip("=")


def _authorize_event_rsvp_read(*, event: dict[str, Any], caller_user_id: str | None, is_admin: bool) -> None:
    """Enforce creator/admin-only RSVP visibility for an existing event."""
    if is_admin:
        return

    if caller_user_id is None:
        raise PermissionError(RSVP_READ_FORBIDDEN_MESSAGE)

    if caller_user_id != event["created_by"]:
        raise PermissionError(RSVP_READ_FORBIDDEN_MESSAGE)


def _build_event_key(event_id: str) -> dict[str, dict[str, str]]:
    """Build the low-level DynamoDB primary key for one event item."""
    return {
        "event_pk": {"S": f"EVENT#{event_id}"},
    }


def _build_rsvps_query_values(event_id: str) -> dict[str, dict[str, str]]:
    """Build the low-level DynamoDB expression values for one RSVP event query."""
    return {
        ":event_pk": {"S": f"EVENT#{event_id}"},
    }


def _deserialize_event_item(item: dict[str, Any]) -> dict[str, Any]:
    """Deserialize one low-level DynamoDB event item into the canonical read shape."""
    return {
        "event_id": _deserialize_event_id(item.get("event_pk")),
        "status": _deserialize_status(item.get("status")),
        "title": _deserialize_event_required_string(item.get("title"), field_name="title"),
        "date": _deserialize_event_required_string(item.get("date"), field_name="date"),
        "capacity": _deserialize_capacity(item.get("capacity")),
        "created_by": _deserialize_event_required_string(item.get("creator_id"), field_name="creator_id"),
        "rsvp_total": _deserialize_event_counter(item.get("rsvp_total"), field_name="rsvp_total"),
        "attending_count": _deserialize_event_counter(item.get("attending_count"), field_name="attending_count"),
        "not_attending_count": _deserialize_event_counter(item.get("not_attending_count"), field_name="not_attending_count"),
    }


def _deserialize_rsvp_item(item: dict[str, Any]) -> dict[str, Any]:
    """Deserialize one low-level DynamoDB RSVP item into the canonical read shape."""
    subject_type = _deserialize_rsvp_required_string(item.get("subject_type"), field_name="subject_type")
    user_id = _deserialize_rsvp_optional_string(item.get("user_id"), field_name="user_id")

    if subject_type == "USER":
        if user_id is None or not user_id.strip():
            raise RsvpStateError("Stored USER RSVP items must include user_id.")
    elif subject_type == "ANON":
        user_id = None
    else:
        raise RsvpStateError("Stored subject_type must be USER or ANON.")

    return {
        "subject_type": subject_type,
        "user_id": user_id,
        "attending": _deserialize_rsvp_bool(item.get("attending"), field_name="attending"),
        "created_at": _deserialize_rsvp_required_string(item.get("created_at"), field_name="created_at"),
        "updated_at": _deserialize_rsvp_required_string(item.get("updated_at"), field_name="updated_at"),
    }


def _query_rsvps(*, client: Any, event_id: str, limit: int, next_cursor: dict[str, Any] | None) -> dict[str, Any]:
    """Query RSVP items for an event."""
    rsvps_table_name = _get_required_env("RSVPS_TABLE_NAME")

    query_kwargs: dict[str, Any] = {
        "TableName": rsvps_table_name,
        "KeyConditionExpression": "event_pk = :event_pk",
        "ExpressionAttributeValues": _build_rsvps_query_values(event_id),
        "Limit": limit,
        "ScanIndexForward": True,
    }

    if next_cursor is not None:
        query_kwargs["ExclusiveStartKey"] = next_cursor

    logger.info("querying RSVP items for event %s with limit %s", event_id, limit)
    response = client.query(**query_kwargs)

    raw_items = response.get("Items", [])
    if not isinstance(raw_items, list):
        raise RsvpStateError("Stored DynamoDB RSVP query Items payload must be a list.")

    items: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            raise RsvpStateError("Each stored DynamoDB RSVP item must be an object.")
        items.append(_deserialize_rsvp_item(item))

    return {
        "items": items,
        "next_cursor": _encode_cursor(response.get("LastEvaluatedKey")),
    }


def _build_event_summary(event: dict[str, Any]) -> dict[str, Any]:
    """Map canonical event item to the compact event summary DTO."""
    return {
        "event_id": event["event_id"],
        "status": event["status"],
        "title": event["title"],
        "date": event["date"],
        "capacity": event["capacity"],
        "created_by": event["created_by"],
        "rsvp_count": event["rsvp_total"],
        "attending_count": event["attending_count"],
    }


def _map_rsvp_item_to_dto(item: dict[str, Any]) -> dict[str, Any]:
    """Map canonical RSVP item to the public RSVP list item DTO."""
    if item["subject_type"] == "USER":
        subject = {
            "type": "USER",
            "user_id": item["user_id"],
            "anonymous": False,
        }
    else:
        subject = {
            "type": "ANON",
            "user_id": None,
            "anonymous": True,
        }

    return {
        "subject": subject,
        "attending": item["attending"],
        "created_at": item["created_at"],
        "updated_at": item["updated_at"],
    }


def _build_stats(event: dict[str, Any]) -> dict[str, int]:
    """Build global RSVP stats from the canonical event helper counters."""
    return {
        "total": event["rsvp_total"],
        "attending": event["attending_count"],
        "not_attending": event["not_attending_count"],
    }


def _deserialize_event_id(value: Any) -> str:
    """Deserialize the internal event_pk value into the public event identifier."""
    if not isinstance(value, dict) or value.get("S") is None:
        raise EventStateError("Stored event_pk must be a DynamoDB string attribute.")

    event_pk = value["S"]
    if not isinstance(event_pk, str) or not event_pk.startswith("EVENT#"):
        raise EventStateError("Stored event_pk must use the EVENT# prefix.")

    event_id = event_pk.removeprefix("EVENT#")
    if not event_id:
        raise EventStateError("Stored event_pk must contain a public identifier.")

    return event_id


def _deserialize_status(value: Any) -> str:
    """Deserialize and validate the stored event lifecycle status."""
    status = _deserialize_event_required_string(value, field_name="status")
    if status in {"ACTIVE", "CANCELLED"}:
        return status
    raise EventStateError("Stored status must be ACTIVE or CANCELLED.")


def _deserialize_event_required_string(value: Any, *, field_name: str) -> str:
    """Deserialize a required DynamoDB string attribute from an event item."""
    if not isinstance(value, dict) or value.get("S") is None:
        raise EventStateError(f"Stored {field_name} must be a DynamoDB string attribute.")

    text = value["S"]
    if not isinstance(text, str):
        raise EventStateError(f"Stored {field_name} must be a string.")

    return text


def _deserialize_event_counter(value: Any, *, field_name: str) -> int:
    """Deserialize a required DynamoDB integer counter from an event item."""
    if not isinstance(value, dict) or value.get("N") is None:
        raise EventStateError(f"Stored {field_name} must be a DynamoDB number attribute.")

    raw_number = value["N"]
    if not isinstance(raw_number, str):
        raise EventStateError(f"Stored {field_name} must be a numeric string.")

    decimal_value = Decimal(raw_number)
    if decimal_value % 1 != 0:
        raise EventStateError(f"Stored {field_name} must be an integer.")

    return int(decimal_value)


def _deserialize_capacity(value: Any) -> int | None:
    """Deserialize the stored capacity as integer-or-null."""
    if isinstance(value, dict) and value.get("NULL") is True:
        return None

    return _deserialize_event_counter(value, field_name="capacity")


def _deserialize_rsvp_required_string(value: Any, *, field_name: str) -> str:
    """Deserialize a required DynamoDB string attribute from an RSVP item."""
    if not isinstance(value, dict) or value.get("S") is None:
        raise RsvpStateError(f"Stored {field_name} must be a DynamoDB string attribute.")

    text = value["S"]
    if not isinstance(text, str):
        raise RsvpStateError(f"Stored {field_name} must be a string.")

    return text


def _deserialize_rsvp_optional_string(value: Any, *, field_name: str) -> str | None:
    """Deserialize an optional DynamoDB string attribute from an RSVP item."""
    if value is None:
        return None

    if not isinstance(value, dict) or value.get("S") is None:
        raise RsvpStateError(f"Stored {field_name} must be a DynamoDB string attribute when present.")

    text = value["S"]
    if not isinstance(text, str):
        raise RsvpStateError(f"Stored {field_name} must be a string when present.")

    return text


def _deserialize_rsvp_bool(value: Any, *, field_name: str) -> bool:
    """Deserialize a required DynamoDB boolean attribute from an RSVP item."""
    if not isinstance(value, dict) or "BOOL" not in value:
        raise RsvpStateError(f"Stored {field_name} must be a DynamoDB boolean attribute.")

    bool_value = value["BOOL"]
    if not isinstance(bool_value, bool):
        raise RsvpStateError(f"Stored {field_name} must be a boolean.")

    return bool_value


def _get_required_env(name: str) -> str:
    """Read one required environment variable used by this handler."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _get_dynamodb_client() -> Any:
    """Create the low-level DynamoDB client used by the handler."""
    return boto3.client("dynamodb")


def _success_response(*, status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Return the standard API Gateway-style success response wrapper."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _error_response(*, status_code: int, message: str) -> dict[str, Any]:
    """Return the standard API Gateway-style error response wrapper."""
    return _success_response(status_code=status_code, body={"message": message})
