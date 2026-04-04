import json
import logging
import os
from decimal import Decimal
from typing import Any

import boto3


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class EventDtoMappingError(Exception):
    """Raised when a stored DynamoDB event item does not match the locked DTO contract."""


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # Keep the handler flow small and predictable:
    #
    # 1. validate the incoming event shape
    # 2. resolve the public event identifier from the supported request shapes
    # 3. validate that identifier before reading from DynamoDB
    # 4. read the canonical event item by primary key
    # 5. map the stored item into the locked public DTO
    # 6. return the standard API Gateway-style response wrapper
    #
    # This Lambda is intentionally a public single-item read in the current
    # platform contract, so there is no caller-context, ownership, or admin
    # authorization step here.
    logger.info("get-event invocation started")

    try:
        if not isinstance(event, dict):
            raise ValueError("Event payload must be a JSON object.")

        event_id = _validate_event_id(event)

        events_table_name = _get_required_env("EVENTS_TABLE_NAME")
        table = _get_dynamodb_table(events_table_name)

        response_body = _get_event(table=table, event_id=event_id)
        logger.info("get-event completed for event_id %s", event_id)

        return _success_response(status_code=200, body=response_body)
    except ValueError as exc:
        # Only caller/request validation problems should end up as 400s.
        logger.info("get-event validation failed: %s", exc)
        return _error_response(status_code=400, message=str(exc))
    except LookupError as exc:
        # A missing item is a normal business outcome for a single-record read.
        logger.info("get-event not found: %s", exc)
        return _error_response(status_code=404, message=str(exc))
    except EventDtoMappingError:
        # If the stored DynamoDB item no longer matches the canonical event
        # shape, that is an internal runtime/data problem, not a bad request.
        logger.exception("get-event encountered an invalid stored event shape")
        return _error_response(status_code=500, message="Internal server error.")
    except Exception:
        logger.exception("get-event failed unexpectedly")
        return _error_response(status_code=500, message="Internal server error.")


def _validate_event_id(request: dict[str, Any]) -> str:
    # The public identifier can arrive either from future path parameters or
    # from a simple top-level field used in direct invocation and tests.
    #
    # We intentionally prefer pathParameters.event_id first so this handler
    # already matches the future GET /api/events/{event_id} route shape.
    raw_event_id = _resolve_event_id(request)

    if raw_event_id is None:
        raise ValueError("event_id is required.")

    if not isinstance(raw_event_id, str):
        raise ValueError("event_id must be a non-empty string.")

    event_id = raw_event_id.strip()
    if not event_id:
        raise ValueError("event_id must be a non-empty string.")

    # Callers should use only the public identifier. The internal DynamoDB
    # storage key is a backend concern and should never be sent by clients.
    if event_id.startswith("EVENT#"):
        raise ValueError("event_id must use the public identifier, not the internal storage key.")

    return event_id


def _resolve_event_id(request: dict[str, Any]) -> Any:
    # Keep the resolution order explicit and easy to reason about:
    #
    # 1. pathParameters.event_id
    # 2. top-level event_id
    #
    # That gives future API Gateway requests priority without making direct
    # invocation harder during the current implementation phase.
    path_parameters = request.get("pathParameters")
    if path_parameters is not None:
        if not isinstance(path_parameters, dict):
            raise ValueError("pathParameters must be an object when provided.")

        if "event_id" in path_parameters:
            return path_parameters.get("event_id")

    return request.get("event_id")


def _get_event(*, table: Any, event_id: str) -> dict[str, Any]:
    # Single-item event lookup should use DynamoDB's direct primary-key read.
    #
    # This is not a scan, query, or GSI use case because we already know the
    # one exact record we want: EVENT#<public-id>.
    event_pk = f"EVENT#{event_id}"
    logger.info("reading event item %s from DynamoDB", event_pk)
    dynamodb_response = table.get_item(Key={"event_pk": event_pk})

    item = dynamodb_response.get("Item")
    if item is None:
        raise LookupError("Event not found.")

    # boto3 normally returns Item as a dictionary, but keeping a defensive
    # guard here makes the boundary clearer and prevents odd runtime leakage.
    if not isinstance(item, dict):
        raise EventDtoMappingError("Stored DynamoDB item must be an object.")

    return {
        # Keep the single-item response family aligned with list-events:
        # list-events returns {"items": [...]}
        # get-event returns {"item": {...}}
        "item": _to_event_dto(item),
    }


def _to_event_dto(item: dict[str, Any]) -> dict[str, Any]:
    # Map the internal DynamoDB event record into the stable public event DTO.
    #
    # This is intentionally strict. If the stored item no longer matches the
    # canonical platform event shape, that should fail as an internal error
    # instead of silently returning a misleading best-effort response.
    #
    # The DTO is the same public shape already locked for list-events, so
    # get-event becomes the single-item companion to that collection read.
    return {
        "event_id": _to_event_id(item.get("event_pk")),
        "title": _normalize_text(item.get("title"), field_name="title"),
        # The DTO contract says all fields must always be present. Canonical
        # event records should normally have real date values, but the mapper
        # still normalizes missing text-like fields to empty strings to stay
        # consistent with the currently locked contract.
        "date": _normalize_text(item.get("date"), field_name="date"),
        "description": _normalize_text(item.get("description"), field_name="description"),
        "location": _normalize_text(item.get("location"), field_name="location"),
        # Capacity stays numeric-or-null in the public DTO.
        # A null capacity means unlimited attendance.
        "capacity": _normalize_capacity(item.get("capacity")),
        "is_public": _normalize_bool(item.get("is_public"), field_name="is_public"),
        "requires_admin": _normalize_bool(item.get("requires_admin"), field_name="requires_admin"),
        "created_by": _normalize_text(item.get("creator_id"), field_name="creator_id"),
        # Just like date, created_at should normally be present on canonical
        # records, but the DTO still guarantees presence of the field itself.
        "created_at": _normalize_text(item.get("created_at"), field_name="created_at"),
        "rsvp_count": _normalize_counter(item.get("rsvp_total"), field_name="rsvp_total"),
        "attending_count": _normalize_counter(item.get("attending_count"), field_name="attending_count"),
    }


def _to_event_id(raw_event_pk: Any) -> str:
    # DynamoDB stores events under keys such as:
    #   EVENT#12345678-1234-1234-1234-123456789abc
    #
    # But the public API should expose only:
    #   12345678-1234-1234-1234-123456789abc
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
    #
    # The frontend can later render null capacity as "Unlimited" for people,
    # but the API should keep the field machine-friendly and type-stable.
    if value is None:
        return None

    if isinstance(value, bool):
        raise EventDtoMappingError("Stored capacity must be an integer or null.")

    if isinstance(value, int):
        return value

    # Real DynamoDB number attributes often come back from boto3 as Decimal,
    # so the mapper must normalize integral values back into plain Python ints.
    if isinstance(value, Decimal):
        if value % 1 != 0:
            raise EventDtoMappingError("Stored capacity must be an integer or null.")

        return int(value)

    raise EventDtoMappingError("Stored capacity must be an integer or null.")


def _normalize_bool(value: Any, *, field_name: str) -> bool:
    # These flags are part of the canonical stored event shape, so by the time
    # they reach the mapper they should already be true booleans.
    if isinstance(value, bool):
        return value

    raise EventDtoMappingError(f"Stored {field_name} must be a boolean.")


def _normalize_counter(value: Any, *, field_name: str) -> int:
    # RSVP counters are always exposed as integers in the public DTO.
    #
    # Just like capacity, DynamoDB may return them as Decimal through boto3, so
    # we normalize integral Decimal values back into plain ints here.
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
    # Create the DynamoDB table resource lazily so importing this module does
    # not require ambient AWS configuration during tests.
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
