import base64
import json
import logging
import os
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key


logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Keep the public request contract small and explicit.
DEFAULT_MODE = "all"
ALLOWED_MODES = {"all", "mine"}
DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class EventDtoMappingError(Exception):
    """Raised when a stored DynamoDB event item does not match the locked DTO contract."""


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # Keep the handler flow easy to follow:
    # 1. extract request parameters from the supported event shapes
    # 2. validate mode, limit, cursor, and caller context when needed
    # 3. read from DynamoDB using the access path that matches the mode
    # 4. map storage items into the public event DTO
    # 5. return an API Gateway-style wrapped response
    logger.info("list-events invocation started")

    try:
        request = _extract_request(event)
        validated_request = _validate_request(request=request, event=event)

        events_table_name = _get_required_env("EVENTS_TABLE_NAME")
        table = _get_dynamodb_table(events_table_name)

        response_body = _list_events(table=table, request=validated_request)
        logger.info(
            "list-events completed in mode %s with %s items",
            validated_request["mode"],
            len(response_body["items"]),
        )

        return _success_response(status_code=200, body=response_body)
    except ValueError as exc:
        # Only caller/request validation problems should end up as 400s.
        logger.info("list-events validation failed: %s", exc)
        return _error_response(status_code=400, message=str(exc))
    except EventDtoMappingError:
        # If a stored DynamoDB item no longer matches the canonical event
        # shape, that is an internal runtime/data problem, not a bad request.
        logger.exception("list-events encountered an invalid stored event shape")
        return _error_response(status_code=500, message="Internal server error.")
    except Exception:
        logger.exception("list-events failed unexpectedly")
        return _error_response(status_code=500, message="Internal server error.")


def _extract_request(event: dict[str, Any]) -> dict[str, Any]:
    # This Lambda supports two request shapes:
    #
    # 1. direct invocation:
    #    {
    #      "mode": "all",
    #      "limit": 10
    #    }
    #
    # 2. API Gateway-style query parameters:
    #    {
    #      "queryStringParameters": {
    #        "mode": "mine",
    #        "limit": "10"
    #      }
    #    }
    #
    # For list-style reads we do not need a JSON request body, so this handler
    # reads from top-level fields or queryStringParameters instead.
    if not isinstance(event, dict):
        raise ValueError("Event payload must be a JSON object.")

    query_params = event.get("queryStringParameters")
    if query_params is None:
        return event

    if not isinstance(query_params, dict):
        raise ValueError("queryStringParameters must be an object when provided.")

    return query_params


def _validate_request(*, request: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    # Validate the small public request contract first, then resolve caller
    # context only for the mode that actually needs it.
    mode = str(request.get("mode", DEFAULT_MODE)).strip() or DEFAULT_MODE
    if mode not in ALLOWED_MODES:
        raise ValueError("mode must be one of: all, mine.")

    limit = _validate_limit(request.get("limit"))
    next_cursor = _decode_cursor(request.get("next_cursor"))

    validated_request = {
        "mode": mode,
        "limit": limit,
        "next_cursor": next_cursor,
    }

    # Broad listing is intentionally public for now, but "mine" depends on
    # caller identity because it lists events created by the current user.
    if mode == "mine":
        validated_request["user_id"] = _get_caller_user_id(event)

    return validated_request


def _validate_limit(raw_value: Any) -> int:
    # Support both direct numeric values and API Gateway string values while
    # keeping pagination input simple and bounded.
    if raw_value is None or raw_value == "":
        return DEFAULT_LIMIT

    if isinstance(raw_value, bool):
        raise ValueError(f"limit must be an integer between 1 and {MAX_LIMIT}.")

    if isinstance(raw_value, int):
        limit = raw_value
    elif isinstance(raw_value, str):
        candidate = raw_value.strip()
        if not candidate:
            return DEFAULT_LIMIT

        try:
            limit = int(candidate)
        except ValueError as exc:
            raise ValueError(f"limit must be an integer between 1 and {MAX_LIMIT}.") from exc
    else:
        raise ValueError(f"limit must be an integer between 1 and {MAX_LIMIT}.")

    if limit < 1 or limit > MAX_LIMIT:
        raise ValueError(f"limit must be an integer between 1 and {MAX_LIMIT}.")

    return limit


def _decode_cursor(raw_value: Any) -> dict[str, Any] | None:
    # The client should see next_cursor as an opaque string. Internally we
    # encode DynamoDB LastEvaluatedKey as base64-url JSON so the public API
    # does not expose raw key structure directly.
    if raw_value is None:
        return None

    if not isinstance(raw_value, str):
        raise ValueError("next_cursor must be a valid opaque cursor.")

    candidate = raw_value.strip()
    if not candidate:
        return None

    padding = "=" * (-len(candidate) % 4)

    try:
        decoded_bytes = base64.urlsafe_b64decode(candidate + padding)
        decoded_payload = json.loads(decoded_bytes.decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError("next_cursor must be a valid opaque cursor.") from exc

    if not isinstance(decoded_payload, dict):
        raise ValueError("next_cursor must be a valid opaque cursor.")

    return decoded_payload


def _encode_cursor(last_evaluated_key: dict[str, Any] | None) -> str | None:
    # Return None when there is no next page. Otherwise, turn DynamoDB's raw
    # key state into the opaque cursor that the API returns to the caller.
    if not last_evaluated_key:
        return None

    payload = json.dumps(last_evaluated_key, separators=(",", ":"), sort_keys=True)
    encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")
    return encoded.rstrip("=")


def _get_caller_user_id(event: dict[str, Any]) -> str:
    # Keep direct invocation and tests aligned with the future API Gateway
    # authorizer handoff: caller identity lives in requestContext.authorizer.
    request_context = event.get("requestContext", {})
    if not isinstance(request_context, dict):
        raise ValueError("Authenticated caller context is required for mode=mine.")

    authorizer = request_context.get("authorizer", {})
    if not isinstance(authorizer, dict):
        raise ValueError("Authenticated caller context is required for mode=mine.")

    user_id = str(authorizer.get("user_id", "")).strip()
    if not user_id:
        raise ValueError("Authenticated caller context is required for mode=mine.")

    return user_id


def _list_events(*, table: Any, request: dict[str, Any]) -> dict[str, Any]:
    # Choose the DynamoDB access path that matches the requested listing mode.
    if request["mode"] == "all":
        dynamodb_response = _scan_all_events(
            table=table,
            limit=request["limit"],
            next_cursor=request["next_cursor"],
        )
    else:
        dynamodb_response = _query_creator_events(
            table=table,
            user_id=request["user_id"],
            limit=request["limit"],
            next_cursor=request["next_cursor"],
        )

    items = [_to_event_dto(item) for item in _validate_items(dynamodb_response.get("Items", []))]

    return {
        "items": items,
        "next_cursor": _encode_cursor(dynamodb_response.get("LastEvaluatedKey")),
        "mode": request["mode"],
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


def _scan_all_events(*, table: Any, limit: int, next_cursor: dict[str, Any] | None) -> dict[str, Any]:
    # Broad listing is intentionally scan-backed for now because the current
    # product behavior still allows "show me all events". This is a temporary
    # implementation tradeoff, not the long-term DynamoDB direction.
    scan_kwargs: dict[str, Any] = {"Limit": limit}
    if next_cursor:
        scan_kwargs["ExclusiveStartKey"] = next_cursor

    return table.scan(**scan_kwargs)


def _query_creator_events(
    *,
    table: Any,
    user_id: str,
    limit: int,
    next_cursor: dict[str, Any] | None,
) -> dict[str, Any]:
    # "mine" already has a dedicated access pattern, so use the creator-events
    # GSI instead of falling back to a table scan.
    query_kwargs: dict[str, Any] = {
        "IndexName": "creator-events",
        "KeyConditionExpression": Key("creator_events_gsi_pk").eq(f"CREATOR#{user_id}"),
        "Limit": limit,
    }

    if next_cursor:
        query_kwargs["ExclusiveStartKey"] = next_cursor

    return table.query(**query_kwargs)


def _to_event_dto(item: dict[str, Any]) -> dict[str, Any]:
    # Map the internal DynamoDB event record into the stable public event DTO.
    #
    # This is intentionally strict. If the stored item no longer matches the
    # canonical platform event shape, that should fail as an internal error
    # instead of silently returning a misleading best-effort response.
    return {
        "event_id": _to_event_id(item.get("event_pk")),
        "title": _normalize_text(item.get("title"), field_name="title"),
        "date": _normalize_text(item.get("date"), field_name="date"),
        "description": _normalize_text(item.get("description"), field_name="description"),
        "location": _normalize_text(item.get("location"), field_name="location"),
        # Capacity stays numeric-or-null in the DTO. A null capacity means the
        # event has no explicit attendance limit configured.
        "capacity": _normalize_capacity(item.get("capacity")),
        "is_public": _normalize_bool(item.get("is_public"), field_name="is_public"),
        "requires_admin": _normalize_bool(item.get("requires_admin"), field_name="requires_admin"),
        "created_by": _normalize_text(item.get("creator_id"), field_name="creator_id"),
        "created_at": _normalize_text(item.get("created_at"), field_name="created_at"),
        "rsvp_count": _normalize_counter(item.get("rsvp_total"), field_name="rsvp_total"),
        "attending_count": _normalize_counter(item.get("attending_count"), field_name="attending_count"),
    }


def _to_event_id(raw_event_pk: Any) -> str:
    # Storage uses EVENT#<uuid> while the public DTO should expose only the
    # event identifier itself.
    #
    # This mapping is part of the locked DTO contract, so malformed storage
    # keys should fail fast instead of leaking a best-effort value.
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
    # The DTO contract says all text fields should always be present.
    # Missing text values therefore become empty strings instead of missing keys.
    #
    # We stay strict about unexpected non-string values because stringifying
    # arbitrary lists or dicts would hide bad stored data instead of surfacing it.
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    raise EventDtoMappingError(f"Stored {field_name} must be a string or null.")


def _normalize_capacity(value: Any) -> int | None:
    # Capacity is intentionally numeric-or-null in the public DTO.
    # A null value means unlimited attendance.
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
    # DynamoDB-backed event flags should always be booleans by the time they
    # reach this mapper.
    if isinstance(value, bool):
        return value

    raise EventDtoMappingError(f"Stored {field_name} must be a boolean.")


def _normalize_counter(value: Any, *, field_name: str) -> int:
    # Counters are always present in the platform's canonical event item
    # design, so the public DTO keeps them as integers.
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
