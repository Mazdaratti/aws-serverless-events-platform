import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError

from shared.auth import require_authenticated_caller


logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Keep the public update contract explicit and easy to audit.
MUTABLE_FIELDS = {
    "title",
    "date",
    "description",
    "location",
    "capacity",
    "is_public",
    "requires_admin",
}
IMMUTABLE_FIELDS = {
    "event_id",
    "status",
    "created_by",
    "created_at",
    "rsvp_count",
    "attending_count",
}


class EventDtoMappingError(Exception):
    """Raised when a stored DynamoDB event item does not match the locked DTO contract."""


class ConditionalUpdateStateError(Exception):
    """Raised when a conditional write fails for an unexpected internal reason."""


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # Keep the handler flow small and predictable:
    #
    # 1. validate the top-level event shape
    # 2. resolve caller context, event identifier, and update payload
    # 3. validate the requested field changes
    # 4. read the current event item
    # 5. enforce existence, authorization, and business rules
    # 6. compute the effective post-update state and helper attributes
    # 7. issue a conditional DynamoDB UpdateItem
    # 8. return the updated public event DTO in the standard wrapper
    logger.info("update-event invocation started")

    try:
        if not isinstance(event, dict):
            raise ValueError("Event payload must be a JSON object.")

        # Protected routes should resolve the authenticated caller once at the
        # handler edge, then pass the normalized caller shape through the rest
        # of the business flow.
        caller_context = require_authenticated_caller(event)
        event_id = _validate_event_id(event)
        payload = _extract_payload(event)
        validated_updates = _validate_update_payload(payload=payload, caller_context=caller_context)

        events_table_name = _get_required_env("EVENTS_TABLE_NAME")
        table = _get_dynamodb_table(events_table_name)

        response_body = _update_event(
            table=table,
            event_id=event_id,
            caller_context=caller_context,
            updates=validated_updates,
        )
        logger.info("update-event completed for event_id %s", event_id)

        return _success_response(status_code=200, body=response_body)
    except ValueError as exc:
        logger.info("update-event validation failed: %s", exc)
        return _error_response(status_code=400, message=str(exc))
    except PermissionError as exc:
        logger.info("update-event authorization failed: %s", exc)
        return _error_response(status_code=403, message=str(exc))
    except LookupError as exc:
        logger.info("update-event not found: %s", exc)
        return _error_response(status_code=404, message=str(exc))
    except EventDtoMappingError:
        logger.exception("update-event encountered an invalid stored event shape")
        return _error_response(status_code=500, message="Internal server error.")
    except ConditionalUpdateStateError:
        logger.exception("update-event conditional write failed for an unexpected internal state")
        return _error_response(status_code=500, message="Internal server error.")
    except Exception:
        logger.exception("update-event failed unexpectedly")
        return _error_response(status_code=500, message="Internal server error.")


def _validate_event_id(event: dict[str, Any]) -> str:
    # Keep the identifier resolution order explicit:
    # 1. pathParameters.event_id
    # 2. top-level event_id
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


def _extract_payload(event: dict[str, Any]) -> dict[str, Any]:
    # Payload resolution is intentionally unambiguous:
    #
    # - if body is present, body is the payload source
    # - otherwise, top-level fields are the direct-invocation payload source
    #
    # We do not merge body fields with top-level mutable fields.
    if "body" in event:
        body = event["body"]

        if not isinstance(body, str):
            raise ValueError("Request body must contain valid JSON.")

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must contain valid JSON.") from exc

        if not isinstance(payload, dict):
            raise ValueError("Request body JSON must be an object.")

        return payload

    # Direct invocation keeps event_id at the top level for identifier
    # resolution, but identity/helper envelope fields should not be treated as
    # part of the mutable payload. This keeps direct-invocation tests aligned
    # with the same business payload shape used after routed auth handling.
    return {
        key: value
        for key, value in event.items()
        if key not in {"pathParameters", "requestContext", "caller", "event_id", "body"}
    }


def _validate_update_payload(*, payload: dict[str, Any], caller_context: dict[str, Any]) -> dict[str, Any]:
    # Reject unsupported fields first so callers get a crisp contract error
    # before any field-level normalization starts.
    if not isinstance(payload, dict):
        raise ValueError("Update payload must be an object.")

    if not payload:
        raise ValueError("At least one mutable field must be provided.")

    unknown_fields = sorted(
        key for key in payload.keys() if key not in MUTABLE_FIELDS and key not in IMMUTABLE_FIELDS
    )
    if unknown_fields:
        raise ValueError(f"Unknown update fields are not allowed: {', '.join(unknown_fields)}.")

    immutable_fields = sorted(key for key in payload.keys() if key in IMMUTABLE_FIELDS)
    if immutable_fields:
        raise ValueError(f"Immutable fields cannot be updated: {', '.join(immutable_fields)}.")

    mutable_payload = {key: value for key, value in payload.items() if key in MUTABLE_FIELDS}
    if not mutable_payload:
        raise ValueError("At least one mutable field must be provided.")

    validated_updates: dict[str, Any] = {}

    if "title" in mutable_payload:
        title = mutable_payload["title"]
        if not isinstance(title, str):
            raise ValueError("title must be a non-empty string when provided.")

        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("title must be a non-empty string when provided.")

        validated_updates["title"] = normalized_title

    if "date" in mutable_payload:
        validated_updates["date"] = _normalize_event_date(mutable_payload["date"])

    if "description" in mutable_payload:
        description = mutable_payload["description"]
        if not isinstance(description, str):
            raise ValueError("description must be a string when provided.")
        validated_updates["description"] = description

    if "location" in mutable_payload:
        location = mutable_payload["location"]
        if not isinstance(location, str):
            raise ValueError("location must be a string when provided.")
        validated_updates["location"] = location

    if "capacity" in mutable_payload:
        validated_updates["capacity"] = _validate_capacity(mutable_payload["capacity"])

    if "is_public" in mutable_payload:
        validated_updates["is_public"] = _coerce_bool(mutable_payload["is_public"], "is_public")

    if "requires_admin" in mutable_payload:
        requires_admin = _coerce_bool(mutable_payload["requires_admin"], "requires_admin")
        if requires_admin and not caller_context["is_admin"]:
            raise ValueError("admin privileges are required to make an event admin-only.")
        validated_updates["requires_admin"] = requires_admin

    if not validated_updates:
        raise ValueError("At least one mutable field must be provided.")

    return validated_updates


def _validate_capacity(value: Any) -> int | None:
    if value is None:
        return None

    if isinstance(value, bool):
        raise ValueError("capacity must be null or an integer greater than or equal to 1.")

    if not isinstance(value, int):
        raise ValueError("capacity must be null or an integer greater than or equal to 1.")

    if value < 1:
        raise ValueError("capacity must be null or an integer greater than or equal to 1.")

    return value


def _update_event(
    *,
    table: Any,
    event_id: str,
    caller_context: dict[str, Any],
    updates: dict[str, Any],
) -> dict[str, Any]:
    event_pk = f"EVENT#{event_id}"
    logger.info("reading current event item %s from DynamoDB", event_pk)
    current_response = table.get_item(Key={"event_pk": event_pk})

    current_item = current_response.get("Item")
    if current_item is None:
        raise LookupError("Event not found.")

    if not isinstance(current_item, dict):
        raise EventDtoMappingError("Stored DynamoDB item must be an object.")

    current_state = _to_internal_event_state(current_item)
    _authorize_update(caller_context=caller_context, current_state=current_state)
    _validate_business_rules(updates=updates, current_state=current_state)

    effective_state = _build_effective_state(
        event_id=event_id,
        current_state=current_state,
        updates=updates,
    )
    update_expression = _build_update_expression(
        effective_state=effective_state,
        updates=updates,
    )

    logger.info("updating event item %s in DynamoDB", event_pk)
    try:
        update_response = table.update_item(
            Key={"event_pk": event_pk},
            UpdateExpression=update_expression["update_expression"],
            ExpressionAttributeNames=update_expression["expression_attribute_names"],
            ExpressionAttributeValues=update_expression["expression_attribute_values"],
            ConditionExpression=update_expression["condition_expression"],
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            raise

        _handle_conditional_update_failure(
            table=table,
            event_id=event_id,
            updates=updates,
        )
        raise

    updated_item = update_response.get("Attributes")
    if not isinstance(updated_item, dict):
        raise EventDtoMappingError("Updated DynamoDB item must be an object.")

    return {"item": _to_event_dto(updated_item)}


def _handle_conditional_update_failure(*, table: Any, event_id: str, updates: dict[str, Any]) -> None:
    # A conditional write can fail because the item disappeared or because
    # attending_count changed after our initial read. Re-read so we can return
    # the correct business status instead of collapsing everything into 500.
    event_pk = f"EVENT#{event_id}"
    latest_response = table.get_item(Key={"event_pk": event_pk})
    latest_item = latest_response.get("Item")

    if latest_item is None:
        raise LookupError("Event not found.")

    if not isinstance(latest_item, dict):
        raise EventDtoMappingError("Stored DynamoDB item must be an object.")

    latest_state = _to_internal_event_state(latest_item)

    if "capacity" in updates and updates["capacity"] is not None:
        if updates["capacity"] < latest_state["attending_count"]:
            raise ValueError("capacity cannot be reduced below the current number of attending RSVPs.")

    raise ConditionalUpdateStateError(
        "Conditional update failed for an unexpected internal state transition."
    )


def _to_internal_event_state(item: dict[str, Any]) -> dict[str, Any]:
    # Read only the fields needed for authorization, business rules, and helper
    # attribute recomputation. This stays separate from the public DTO mapper
    # because update logic needs the storage-facing view of the record.
    return {
        "event_id": _to_event_id(item.get("event_pk")),
        "status": _normalize_status(item.get("status")),
        "creator_id": _normalize_required_text(item.get("creator_id"), field_name="creator_id"),
        "date": _normalize_required_text(item.get("date"), field_name="date"),
        "is_public": _normalize_bool(item.get("is_public"), field_name="is_public"),
        "requires_admin": _normalize_bool(item.get("requires_admin"), field_name="requires_admin"),
        "attending_count": _normalize_counter(item.get("attending_count"), field_name="attending_count"),
    }


def _authorize_update(*, caller_context: dict[str, Any], current_state: dict[str, Any]) -> None:
    if caller_context["is_admin"]:
        return

    if caller_context["user_id"] == current_state["creator_id"]:
        return

    raise PermissionError("You are not allowed to update this event.")


def _validate_business_rules(*, updates: dict[str, Any], current_state: dict[str, Any]) -> None:
    if current_state["status"] == "CANCELLED":
        raise ValueError("Cancelled events cannot be updated.")

    if "capacity" not in updates:
        return

    capacity = updates["capacity"]
    if capacity is None:
        return

    if capacity < current_state["attending_count"]:
        raise ValueError("capacity cannot be reduced below the current number of attending RSVPs.")


def _build_effective_state(
    *,
    event_id: str,
    current_state: dict[str, Any],
    updates: dict[str, Any],
) -> dict[str, Any]:
    # Compute the final post-update values before building the DynamoDB
    # expression. GSI helper attributes should depend on the effective state,
    # not only on which fields the caller explicitly provided.
    new_date = updates.get("date", current_state["date"])
    new_is_public = updates.get("is_public", current_state["is_public"])

    effective_state = {
        "event_id": event_id,
        "date": new_date,
        "is_public": new_is_public,
        "creator_events_gsi_sk": f"{new_date}#{event_id}",
    }

    if new_is_public:
        effective_state["public_upcoming_gsi_pk"] = "PUBLIC"
        effective_state["public_upcoming_gsi_sk"] = f"{new_date}#{event_id}"

    return effective_state


def _build_update_expression(
    *,
    effective_state: dict[str, Any],
    updates: dict[str, Any],
) -> dict[str, Any]:
    # Update only fields the caller actually sent, then append helper-attribute
    # changes that keep the GSIs consistent with the effective post-update state.
    set_parts: list[str] = []
    remove_parts: list[str] = []
    expression_attribute_names: dict[str, str] = {}
    expression_attribute_values: dict[str, Any] = {}
    condition_parts = ["attribute_exists(event_pk)"]

    field_name_map = {
        "title": "title",
        "date": "date",
        "description": "description",
        "location": "location",
        "capacity": "capacity",
        "is_public": "is_public",
        "requires_admin": "requires_admin",
    }

    for field_name, value in updates.items():
        name_token = f"#field_{field_name}"
        expression_attribute_names[name_token] = field_name_map[field_name]

        if field_name == "capacity":
            if value is None:
                remove_parts.append(name_token)
            else:
                value_token = f":value_{field_name}"
                expression_attribute_values[value_token] = value
                expression_attribute_values[":capacity_limit"] = value
                expression_attribute_names["#attending_count"] = "attending_count"
                set_parts.append(f"{name_token} = {value_token}")
                condition_parts.append("#attending_count <= :capacity_limit")
            continue

        value_token = f":value_{field_name}"
        expression_attribute_values[value_token] = value
        set_parts.append(f"{name_token} = {value_token}")

    # Keep creator-scoped sort ordering aligned with the effective post-update
    # date so creator-based reads stay correct after event changes.
    expression_attribute_names["#creator_events_gsi_sk"] = "creator_events_gsi_sk"
    expression_attribute_values[":creator_events_gsi_sk"] = effective_state["creator_events_gsi_sk"]
    set_parts.append("#creator_events_gsi_sk = :creator_events_gsi_sk")

    expression_attribute_names["#public_upcoming_gsi_pk"] = "public_upcoming_gsi_pk"
    expression_attribute_names["#public_upcoming_gsi_sk"] = "public_upcoming_gsi_sk"

    if effective_state["is_public"]:
        expression_attribute_values[":public_upcoming_gsi_pk"] = "PUBLIC"
        expression_attribute_values[":public_upcoming_gsi_sk"] = effective_state["public_upcoming_gsi_sk"]
        set_parts.append("#public_upcoming_gsi_pk = :public_upcoming_gsi_pk")
        set_parts.append("#public_upcoming_gsi_sk = :public_upcoming_gsi_sk")
    else:
        remove_parts.append("#public_upcoming_gsi_pk")
        remove_parts.append("#public_upcoming_gsi_sk")

    update_clauses: list[str] = []
    if set_parts:
        update_clauses.append("SET " + ", ".join(set_parts))
    if remove_parts:
        update_clauses.append("REMOVE " + ", ".join(remove_parts))

    return {
        "update_expression": " ".join(update_clauses),
        "expression_attribute_names": expression_attribute_names,
        "expression_attribute_values": expression_attribute_values,
        "condition_expression": " AND ".join(condition_parts),
    }


def _normalize_event_date(raw_value: Any) -> str:
    # Normalize all accepted date inputs into one stored format so DynamoDB
    # items and index sort keys stay consistent.
    if not isinstance(raw_value, str):
        raise ValueError("date must be a string when provided.")

    candidate = raw_value.strip()
    if not candidate:
        raise ValueError("date must not be empty when provided.")

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


def _to_event_dto(item: dict[str, Any]) -> dict[str, Any]:
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
    """Validate and normalize the stored lifecycle status for update-event."""
    # Canonical event records must store one explicit valid lifecycle status.
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
