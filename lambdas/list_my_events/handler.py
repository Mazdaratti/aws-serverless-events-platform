import base64
import json
import logging
import os
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from shared.auth import require_authenticated_caller


logger = logging.getLogger()
logger.setLevel(logging.INFO)


DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class RequestValidationError(ValueError):
    """Raised when request input or caller context is invalid for this handler."""


class EventDtoMappingError(Exception):
    """Raised when a stored DynamoDB event item does not match the locked DTO contract."""


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # Keep this handler focused on one job:
    # 1. resolve the authenticated caller
    # 2. validate pagination input
    # 3. query the creator-events GSI
    # 4. map canonical storage items into the public event DTO
    # 5. return an API Gateway-style wrapped response
    logger.info("list-my-events invocation started")

    try:
        caller = _require_authenticated_caller(event)
        request = _extract_request(event)
        validated_request = _validate_request(request=request, caller=caller)

        events_table_name = _get_required_env("EVENTS_TABLE_NAME")
        table = _get_dynamodb_table(events_table_name)

        response_body = _list_my_events(table=table, request=validated_request)
        logger.info(
            "list-my-events completed for caller %s with %s items",
            validated_request["user_id"],
            len(response_body["items"]),
        )

        return _success_response(status_code=200, body=response_body)
    except RequestValidationError as exc:
        logger.info("list-my-events validation failed: %s", exc)
        return _error_response(status_code=400, message=str(exc))
    except EventDtoMappingError:
        logger.exception("list-my-events encountered an invalid stored event shape")
        return _error_response(status_code=500, message="Internal server error.")
    except Exception:
        logger.exception("list-my-events failed unexpectedly")
        return _error_response(status_code=500, message="Internal server error.")


def _require_authenticated_caller(event: dict[str, Any]) -> dict[str, Any]:
    try:
        return require_authenticated_caller(event)
    except ValueError as exc:
        raise RequestValidationError(str(exc)) from exc


def _extract_request(event: dict[str, Any]) -> dict[str, Any]:
    # This Lambda supports two request shapes:
    #
    # 1. direct invocation:
    #    {
    #      "limit": 10
    #    }
    #
    # 2. API Gateway-style query parameters:
    #    {
    #      "queryStringParameters": {
    #        "limit": "10"
    #      }
    #    }
    #
    # For list-style reads we do not need a JSON request body, so this handler
    # reads from top-level fields or queryStringParameters instead.
    if not isinstance(event, dict):
        raise RequestValidationError("Event payload must be a JSON object.")

    query_params = event.get("queryStringParameters")
    if query_params is None:
        return event

    if not isinstance(query_params, dict):
        raise RequestValidationError("queryStringParameters must be an object when provided.")

    return query_params


def _validate_request(*, request: dict[str, Any], caller: dict[str, Any]) -> dict[str, Any]:
    # The public request contract here stays intentionally small:
    # authenticated caller identity is required, and pagination accepts only
    # limit plus an opaque next_cursor.
    limit = _validate_limit(request.get("limit"))
    next_cursor = _decode_cursor(request.get("next_cursor"))

    return {
        "user_id": caller["user_id"],
        "limit": limit,
        "next_cursor": next_cursor,
    }


def _validate_limit(raw_value: Any) -> int:
    if raw_value is None or raw_value == "":
        return DEFAULT_LIMIT

    if isinstance(raw_value, bool):
        raise RequestValidationError(f"limit must be an integer between 1 and {MAX_LIMIT}.")

    if isinstance(raw_value, int):
        limit = raw_value
    elif isinstance(raw_value, str):
        candidate = raw_value.strip()
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


def _decode_cursor(raw_value: Any) -> dict[str, Any] | None:
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

    return decoded_payload


def _encode_cursor(last_evaluated_key: dict[str, Any] | None) -> str | None:
    if not last_evaluated_key:
        return None

    payload = json.dumps(last_evaluated_key, separators=(",", ":"), sort_keys=True)
    encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")
    return encoded.rstrip("=")


def _list_my_events(*, table: Any, request: dict[str, Any]) -> dict[str, Any]:
    dynamodb_response = _query_creator_events(
        table=table,
        user_id=request["user_id"],
        limit=request["limit"],
        next_cursor=request["next_cursor"],
    )

    raw_items = _validate_items(dynamodb_response.get("Items", []))
    items = [_to_event_dto(item) for item in raw_items]

    return {
        "items": items,
        "next_cursor": _encode_cursor(dynamodb_response.get("LastEvaluatedKey")),
    }


def _validate_items(raw_items: Any) -> list[dict[str, Any]]:
    # boto3 normally returns Items as a list of dictionaries, but validating
    # that boundary keeps malformed runtime data from leaking into the mapper.
    if raw_items is None:
        return []

    if not isinstance(raw_items, list):
        raise EventDtoMappingError("Stored DynamoDB Items payload must be a list.")

    validated_items: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            raise EventDtoMappingError("Each stored DynamoDB event item must be an object.")
        validated_items.append(item)

    return validated_items


def _query_creator_events(
    *,
    table: Any,
    user_id: str,
    limit: int,
    next_cursor: dict[str, Any] | None,
) -> dict[str, Any]:
    # list-my-events has a dedicated access pattern, so this handler should
    # query the creator-events GSI instead of scanning the whole table.
    query_kwargs: dict[str, Any] = {
        "IndexName": "creator-events",
        "KeyConditionExpression": Key("creator_events_gsi_pk").eq(f"CREATOR#{user_id}"),
        "Limit": limit,
    }

    if next_cursor:
        query_kwargs["ExclusiveStartKey"] = next_cursor

    return table.query(**query_kwargs)


def _to_event_dto(item: dict[str, Any]) -> dict[str, Any]:
    # Map the internal DynamoDB event record into the same stable public event
    # DTO already used by list-events and get-event.
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
        "created_by": _normalize_text(item.get("creator_id"), field_name="creator_id"),
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
    # Create the DynamoDB resource lazily so importing this module does not
    # require AWS configuration during tests.
    return boto3.resource("dynamodb").Table(table_name)


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
