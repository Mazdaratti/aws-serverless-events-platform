import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError

from lambdas.shared.auth import resolve_optional_caller


logger = logging.getLogger()
logger.setLevel(logging.INFO)


EVENT_NOT_FOUND_MESSAGE = "Event not found."
CANCELLED_EVENT_MESSAGE = "Cancelled events cannot accept RSVPs."
PAST_EVENT_MESSAGE = "Past events cannot accept RSVPs."
FULL_CAPACITY_MESSAGE = "Event is at full capacity."
PROTECTED_EVENT_AUTH_MESSAGE = "Authentication is required to RSVP to this event."
ADMIN_EVENT_AUTH_MESSAGE = "Admin privileges are required to RSVP to this event."


class EventStateError(Exception):
    """Raised when the stored event item does not match the locked canonical shape."""


class RsvpStateError(Exception):
    """Raised when the stored RSVP item does not match the locked canonical shape."""


class TransactionClassificationError(Exception):
    """Raised when a failed transaction cannot be mapped to a known business result."""


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # Keep the RSVP flow explicit and easy to audit:
    #
    # 1. validate the top-level event shape
    # 2. resolve the request contract and caller context
    # 3. read the current event and validate business rules
    # 4. resolve the canonical RSVP subject
    # 5. read the current RSVP state for that subject
    # 6. compute the change classification and counter deltas
    # 7. perform one DynamoDB transaction
    # 8. return the wrapped response with RSVP item + event summary
    logger.info("rsvp invocation started")

    try:
        if not isinstance(event, dict):
            raise ValueError("Event payload must be a JSON object.")

        request = _resolve_request(event)
        client = _get_dynamodb_client()

        response_body, status_code = _handle_rsvp(client=client, request=request)

        logger.info("rsvp completed for event_id %s", request["event_id"])
        return _success_response(status_code=status_code, body=response_body)
    except ValueError as exc:
        logger.info("rsvp validation failed: %s", exc)
        return _error_response(status_code=400, message=str(exc))
    except PermissionError as exc:
        logger.info("rsvp authorization failed: %s", exc)
        return _error_response(status_code=403, message=str(exc))
    except LookupError as exc:
        logger.info("rsvp event lookup failed: %s", exc)
        return _error_response(status_code=404, message=str(exc))
    except EventStateError:
        logger.exception("rsvp encountered an invalid stored event shape")
        return _error_response(status_code=500, message="Internal server error.")
    except RsvpStateError:
        logger.exception("rsvp encountered an invalid stored RSVP shape")
        return _error_response(status_code=500, message="Internal server error.")
    except TransactionClassificationError:
        logger.exception("rsvp transaction failure could not be classified")
        return _error_response(status_code=500, message="Internal server error.")
    except Exception:
        logger.exception("rsvp failed unexpectedly")
        return _error_response(status_code=500, message="Internal server error.")


def _handle_rsvp(*, client: Any, request: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Execute the locked RSVP flow and return the wrapped body plus HTTP status."""
    now_utc = datetime.now(timezone.utc)
    event_key = _build_event_key(request["event_id"])
    events_table_name = _get_required_env("EVENTS_TABLE_NAME")
    rsvps_table_name = _get_required_env("RSVPS_TABLE_NAME")

    logger.info("reading current event item %s from DynamoDB", event_key["event_pk"]["S"])
    event_response = client.get_item(
        TableName=events_table_name,
        Key=event_key,
    )
    raw_event_item = event_response.get("Item")
    if raw_event_item is None:
        raise LookupError(EVENT_NOT_FOUND_MESSAGE)

    event_state = _deserialize_event_item(raw_event_item)
    _assert_event_active(event_state)
    _assert_event_not_past(event_state, now_utc)
    _assert_rsvp_allowed_for_event_type(event_state, request["caller_context"])

    subject = _resolve_subject(
        caller_context=request["caller_context"],
        payload=request["payload"],
        event_state=event_state,
    )
    rsvp_key = _build_rsvp_key(event_id=request["event_id"], subject_sk=subject["subject_sk"])

    logger.info(
        "reading current RSVP item for event %s and subject_type %s",
        request["event_id"],
        subject["subject_type"],
    )
    rsvp_response = client.get_item(
        TableName=rsvps_table_name,
        Key=rsvp_key,
    )
    raw_rsvp_item = rsvp_response.get("Item")
    current_rsvp = _deserialize_rsvp_item(raw_rsvp_item) if raw_rsvp_item is not None else None

    change = _calculate_rsvp_change(
        previous_attending=current_rsvp["attending"] if current_rsvp is not None else None,
        new_attending=request["attending"],
    )

    _assert_capacity_available(
        event_state=event_state,
        seat_consuming_write=change["seat_consuming_write"],
    )

    rsvp_item = _build_rsvp_item(
        event_id=request["event_id"],
        subject=subject,
        attending=request["attending"],
        current_rsvp=current_rsvp,
        now_utc=now_utc,
    )

    try:
        logger.info(
            "writing RSVP transaction for event %s and subject_type %s",
            request["event_id"],
            subject["subject_type"],
        )
        client.transact_write_items(
            TransactItems=[
                _build_rsvp_put_transaction_item(
                    table_name=rsvps_table_name,
                    rsvp_item=rsvp_item,
                    current_rsvp=current_rsvp,
                ),
                _build_event_update_transaction_item(
                    table_name=events_table_name,
                    event_key=event_key,
                    event_state=event_state,
                    change=change,
                ),
            ]
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "TransactionCanceledException":
            raise

        _reclassify_transaction_failure(
            client=client,
            request=request,
            seat_consuming_write=change["seat_consuming_write"],
        )

    updated_event_state = {
        **event_state,
        "rsvp_total": event_state["rsvp_total"] + change["rsvp_total_delta"],
        "attending_count": event_state["attending_count"] + change["attending_count_delta"],
        "not_attending_count": event_state["not_attending_count"] + change["not_attending_count_delta"],
    }
    stored_rsvp = _deserialize_rsvp_item(rsvp_item)

    return (
        {
            "item": _map_rsvp_response_item(
                event_id=request["event_id"],
                subject=subject,
                rsvp_item=stored_rsvp,
            ),
            "event_summary": _map_event_summary(updated_event_state),
            "operation": change["operation"],
        },
        201 if change["operation"] == "created" else 200,
    )


def _resolve_request(event: dict[str, Any]) -> dict[str, Any]:
    # Keep request resolution centralized so the rest of the handler can work
    # with one normalized contract shape instead of branching on direct-invoke
    # versus API Gateway-style inputs at every step.
    payload = _resolve_request_payload(event)
    caller_context = _resolve_caller_context(event)
    event_id = _resolve_event_id(event)

    return {
        "event_id": _validate_event_id(event_id),
        "attending": _resolve_attending(payload),
        "payload": payload,
        "caller_context": caller_context,
    }


def _resolve_request_payload(event: dict[str, Any]) -> dict[str, Any]:
    # Match the same precedence rule used in the other handlers:
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

    return {
        key: value
        for key, value in event.items()
        if key not in {"pathParameters", "requestContext", "event_id", "body"}
    }


def _resolve_event_id(event: dict[str, Any]) -> Any:
    path_parameters = event.get("pathParameters")
    if path_parameters is not None:
        if not isinstance(path_parameters, dict):
            raise ValueError("pathParameters must be an object when provided.")

        if "event_id" in path_parameters:
            return path_parameters.get("event_id")

    return event.get("event_id")


def _validate_event_id(value: Any) -> str:
    if value is None:
        raise ValueError("event_id is required.")
    if not isinstance(value, str):
        raise ValueError("event_id must be a non-empty string.")

    event_id = value.strip()
    if not event_id:
        raise ValueError("event_id must be a non-empty string.")
    if event_id.startswith("EVENT#"):
        raise ValueError("event_id must use the public identifier, not the internal storage key.")

    return event_id


def _resolve_attending(payload: dict[str, Any]) -> bool:
    if "attending" not in payload:
        raise ValueError("attending is required.")

    attending = payload["attending"]
    if not isinstance(attending, bool):
        raise ValueError("attending must be a boolean.")

    return attending


def _resolve_caller_context(event: dict[str, Any]) -> dict[str, Any]:
    # Keep RSVP on the shared normalized caller contract so the routed
    # business Lambda does not parse raw authorizer shapes itself.
    caller = resolve_optional_caller(event)

    return {
        "authenticated": caller["is_authenticated"],
        "user_id": caller["user_id"],
        "is_admin": caller["is_admin"],
    }


def _resolve_subject(*, caller_context: dict[str, Any], payload: dict[str, Any], event_state: dict[str, Any]) -> dict[str, Any]:
    # Resolve the canonical RSVP subject that will own the one durable RSVP
    # record for this event. This is where overwrite semantics are anchored:
    # one event + one subject => one canonical RSVP item.
    anonymous_token = payload.get("anonymous_token")

    if caller_context["authenticated"]:
        if anonymous_token is not None:
            raise ValueError("anonymous_token must not be provided for authenticated RSVP.")

        return {
            "subject_type": "USER",
            "subject_sk": f"USER#{caller_context['user_id']}",
            "user_id": caller_context["user_id"],
            "anonymous_token": None,
            "anonymous": False,
        }

    if not event_state["is_public"]:
        raise PermissionError(
            PROTECTED_EVENT_AUTH_MESSAGE if not event_state["requires_admin"] else ADMIN_EVENT_AUTH_MESSAGE
        )

    if not isinstance(anonymous_token, str):
        raise ValueError("anonymous_token is required for anonymous RSVP.")

    normalized_token = anonymous_token.strip()
    if not normalized_token:
        raise ValueError("anonymous_token is required for anonymous RSVP.")

    return {
        "subject_type": "ANON",
        "subject_sk": f"ANON#{normalized_token}",
        "user_id": None,
        "anonymous_token": normalized_token,
        "anonymous": True,
    }


def _assert_rsvp_allowed_for_event_type(event_state: dict[str, Any], caller_context: dict[str, Any]) -> None:
    # Keep event-type authorization explicit instead of folding it into generic
    # request parsing. That makes the business rule easier to read:
    #
    # - public: anonymous or authenticated allowed
    # - protected: authenticated required
    # - admin-only: authenticated admin required
    if event_state["requires_admin"]:
        if caller_context["authenticated"] and caller_context["is_admin"]:
            return
        raise PermissionError(ADMIN_EVENT_AUTH_MESSAGE)

    if event_state["is_public"]:
        return

    if caller_context["authenticated"]:
        return

    raise PermissionError(PROTECTED_EVENT_AUTH_MESSAGE)


def _assert_event_active(event_state: dict[str, Any]) -> None:
    if event_state["status"] == "ACTIVE":
        return
    if event_state["status"] == "CANCELLED":
        raise ValueError(CANCELLED_EVENT_MESSAGE)
    raise EventStateError("Stored status must be ACTIVE or CANCELLED.")


def _assert_event_not_past(event_state: dict[str, Any], now_utc: datetime) -> None:
    if event_state["date"] <= now_utc:
        raise ValueError(PAST_EVENT_MESSAGE)


def _assert_capacity_available(*, event_state: dict[str, Any], seat_consuming_write: bool) -> None:
    # Capacity applies only when the write would consume an attendee seat.
    # Non-attending writes and seat-releasing writes must remain allowed even
    # when the event is otherwise full.
    if not seat_consuming_write:
        return
    if event_state["capacity"] is None:
        return
    if event_state["attending_count"] >= event_state["capacity"]:
        raise ValueError(FULL_CAPACITY_MESSAGE)


def _calculate_rsvp_change(*, previous_attending: bool | None, new_attending: bool) -> dict[str, Any]:
    """Return the locked counter deltas and operation metadata for one RSVP transition."""
    if previous_attending is None and new_attending:
        return {
            "operation": "created",
            "change_classification": "created_attending",
            "rsvp_total_delta": 1,
            "attending_count_delta": 1,
            "not_attending_count_delta": 0,
            "seat_consuming_write": True,
        }

    if previous_attending is None and not new_attending:
        return {
            "operation": "created",
            "change_classification": "created_not_attending",
            "rsvp_total_delta": 1,
            "attending_count_delta": 0,
            "not_attending_count_delta": 1,
            "seat_consuming_write": False,
        }

    if previous_attending is True and new_attending is True:
        return {
            "operation": "updated",
            "change_classification": "unchanged_attending",
            "rsvp_total_delta": 0,
            "attending_count_delta": 0,
            "not_attending_count_delta": 0,
            "seat_consuming_write": False,
        }

    if previous_attending is False and new_attending is False:
        return {
            "operation": "updated",
            "change_classification": "unchanged_not_attending",
            "rsvp_total_delta": 0,
            "attending_count_delta": 0,
            "not_attending_count_delta": 0,
            "seat_consuming_write": False,
        }

    if previous_attending is True and new_attending is False:
        return {
            "operation": "updated",
            "change_classification": "changed_to_not_attending",
            "rsvp_total_delta": 0,
            "attending_count_delta": -1,
            "not_attending_count_delta": 1,
            "seat_consuming_write": False,
        }

    return {
        "operation": "updated",
        "change_classification": "changed_to_attending",
        "rsvp_total_delta": 0,
        "attending_count_delta": 1,
        "not_attending_count_delta": -1,
        "seat_consuming_write": True,
    }


def _build_rsvp_item(
    *,
    event_id: str,
    subject: dict[str, Any],
    attending: bool,
    current_rsvp: dict[str, Any] | None,
    now_utc: datetime,
) -> dict[str, Any]:
    # Preserve created_at across overwrites so the record keeps its original
    # creation history, while updated_at reflects the current successful write.
    created_at = current_rsvp["created_at"] if current_rsvp is not None else _to_iso_utc(now_utc)
    updated_at = _to_iso_utc(now_utc)

    item = {
        "event_pk": {"S": f"EVENT#{event_id}"},
        "subject_sk": {"S": subject["subject_sk"]},
        "attending": {"BOOL": attending},
        "created_at": {"S": created_at},
        "updated_at": {"S": updated_at},
        "subject_type": {"S": subject["subject_type"]},
    }

    if subject["user_id"] is not None:
        item["user_id"] = {"S": subject["user_id"]}

    if subject["anonymous_token"] is not None:
        item["anonymous_token"] = {"S": subject["anonymous_token"]}

    return item


def _build_event_key(event_id: str) -> dict[str, Any]:
    return {"event_pk": {"S": f"EVENT#{event_id}"}}


def _build_rsvp_key(*, event_id: str, subject_sk: str) -> dict[str, Any]:
    return {
        "event_pk": {"S": f"EVENT#{event_id}"},
        "subject_sk": {"S": subject_sk},
    }


def _build_rsvp_put_transaction_item(*, table_name: str, rsvp_item: dict[str, Any], current_rsvp: dict[str, Any] | None) -> dict[str, Any]:
    """Build the RSVP transaction item with state-conditional concurrency protection."""
    put_item = {
        "TableName": table_name,
        "Item": rsvp_item,
    }

    if current_rsvp is None:
        put_item["ConditionExpression"] = "attribute_not_exists(event_pk)"
        return {"Put": put_item}

    put_item["ConditionExpression"] = (
        "attribute_exists(event_pk) AND "
        "attribute_exists(subject_sk) AND "
        "attending = :previous_attending AND "
        "created_at = :previous_created_at"
    )
    put_item["ExpressionAttributeValues"] = {
        ":previous_attending": {"BOOL": current_rsvp["attending"]},
        ":previous_created_at": {"S": current_rsvp["created_at"]},
    }
    return {"Put": put_item}


def _build_event_update_transaction_item(
    *,
    table_name: str,
    event_key: dict[str, Any],
    event_state: dict[str, Any],
    change: dict[str, Any],
) -> dict[str, Any]:
    # The event item is the place where aggregate helper counters live, so the
    # RSVP transaction updates those counters in the same durable write that
    # stores the canonical RSVP item.
    expression_attribute_names = {
        "#status": "status",
    }

    if change["seat_consuming_write"] and event_state["capacity"] is not None:
        expression_attribute_names["#attending_count"] = "attending_count"

    return {
        "Update": {
            "TableName": table_name,
            "Key": event_key,
            "UpdateExpression": (
                "SET rsvp_total = rsvp_total + :rsvp_total_delta, "
                "attending_count = attending_count + :attending_delta, "
                "not_attending_count = not_attending_count + :not_attending_delta"
            ),
            "ConditionExpression": _build_event_update_condition(
                seat_consuming_write=change["seat_consuming_write"],
                event_has_capacity=event_state["capacity"] is not None,
            ),
            "ExpressionAttributeNames": expression_attribute_names,
            "ExpressionAttributeValues": _build_event_update_values(
                change=change,
                event_state=event_state,
            ),
        }
    }


def _build_event_update_condition(*, seat_consuming_write: bool, event_has_capacity: bool) -> str:
    # Keep the transactional guard focused on the business conflicts that matter
    # at write time:
    #
    # - the event must still exist
    # - it must still be ACTIVE
    # - if this write consumes a seat, capacity must still be available
    condition_parts = [
        "attribute_exists(event_pk)",
        "#status = :active",
    ]

    if seat_consuming_write and event_has_capacity:
        condition_parts.append("#attending_count < :capacity")

    return " AND ".join(condition_parts)


def _build_event_update_values(*, change: dict[str, Any], event_state: dict[str, Any]) -> dict[str, Any]:
    # Build the DynamoDB attribute values separately so the transaction builder
    # reads more like business intent than serialization noise.
    values = {
        ":rsvp_total_delta": {"N": str(change["rsvp_total_delta"])},
        ":attending_delta": {"N": str(change["attending_count_delta"])},
        ":not_attending_delta": {"N": str(change["not_attending_count_delta"])},
        ":active": {"S": "ACTIVE"},
    }

    if change["seat_consuming_write"] and event_state["capacity"] is not None:
        values[":capacity"] = {"N": str(event_state["capacity"])}

    return values


def _reclassify_transaction_failure(*, client: Any, request: dict[str, Any], seat_consuming_write: bool) -> None:
    """Re-read only the event item and translate a failed transaction into the locked business result."""
    latest_response = client.get_item(
        TableName=_get_required_env("EVENTS_TABLE_NAME"),
        Key=_build_event_key(request["event_id"]),
    )
    raw_latest_item = latest_response.get("Item")
    if raw_latest_item is None:
        raise LookupError(EVENT_NOT_FOUND_MESSAGE)

    latest_event_state = _deserialize_event_item(raw_latest_item)

    if latest_event_state["status"] == "CANCELLED":
        raise ValueError(CANCELLED_EVENT_MESSAGE)

    if seat_consuming_write and latest_event_state["capacity"] is not None:
        if latest_event_state["attending_count"] >= latest_event_state["capacity"]:
            raise ValueError(FULL_CAPACITY_MESSAGE)

    raise TransactionClassificationError("Transaction failure did not match a known business outcome.")


def _deserialize_event_item(raw_item: dict[str, Any]) -> dict[str, Any]:
    """Deserialize the canonical event item shape required by RSVP business logic."""
    if not isinstance(raw_item, dict):
        raise EventStateError("Stored DynamoDB event item must be an object.")

    return {
        "event_id": _to_event_id(raw_item.get("event_pk")),
        "status": _deserialize_event_status(raw_item.get("status")),
        "date": _deserialize_event_date(raw_item.get("date")),
        "is_public": _deserialize_event_bool(raw_item.get("is_public"), field_name="is_public"),
        "requires_admin": _deserialize_event_bool(raw_item.get("requires_admin"), field_name="requires_admin"),
        "capacity": _deserialize_event_optional_number(raw_item.get("capacity"), field_name="capacity"),
        "rsvp_total": _deserialize_event_number(raw_item.get("rsvp_total"), field_name="rsvp_total"),
        "attending_count": _deserialize_event_number(raw_item.get("attending_count"), field_name="attending_count"),
        "not_attending_count": _deserialize_event_number(
            raw_item.get("not_attending_count"),
            field_name="not_attending_count",
        ),
    }


def _deserialize_rsvp_item(raw_item: dict[str, Any]) -> dict[str, Any]:
    """Deserialize the canonical RSVP item shape required for overwrite semantics."""
    if not isinstance(raw_item, dict):
        raise RsvpStateError("Stored DynamoDB RSVP item must be an object.")

    return {
        "event_id": _to_rsvp_event_id(raw_item.get("event_pk")),
        "subject_sk": _deserialize_rsvp_required_string(raw_item.get("subject_sk"), field_name="subject_sk"),
        "attending": _deserialize_rsvp_bool(raw_item.get("attending"), field_name="attending"),
        "created_at": _deserialize_rsvp_required_string(raw_item.get("created_at"), field_name="created_at"),
        "updated_at": _deserialize_rsvp_required_string(raw_item.get("updated_at"), field_name="updated_at"),
        "subject_type": _deserialize_rsvp_required_string(raw_item.get("subject_type"), field_name="subject_type"),
        "user_id": _deserialize_rsvp_optional_string(raw_item.get("user_id"), field_name="user_id"),
        "anonymous_token": _deserialize_rsvp_optional_string(
            raw_item.get("anonymous_token"),
            field_name="anonymous_token",
        ),
    }


def _map_rsvp_response_item(*, event_id: str, subject: dict[str, Any], rsvp_item: dict[str, Any]) -> dict[str, Any]:
    # Return the purpose-built RSVP response shape instead of leaking the raw
    # DynamoDB item or the internal subject key structure.
    return {
        "event_id": event_id,
        "subject": {
            "type": subject["subject_type"],
            "user_id": subject["user_id"],
            "anonymous": subject["anonymous"],
        },
        "attending": rsvp_item["attending"],
        "created_at": rsvp_item["created_at"],
        "updated_at": rsvp_item["updated_at"],
    }


def _map_event_summary(event_state: dict[str, Any]) -> dict[str, Any]:
    # This summary intentionally exposes the current RSVP helper counters because
    # the caller benefits from the updated event state immediately after the
    # transaction succeeds.
    return {
        "status": event_state["status"],
        "capacity": event_state["capacity"],
        "rsvp_count": event_state["rsvp_total"],
        "attending_count": event_state["attending_count"],
        "not_attending_count": event_state["not_attending_count"],
    }


def _to_event_id(attribute_value: Any) -> str:
    event_pk = _deserialize_event_required_string(attribute_value, field_name="event_pk")
    if not event_pk.startswith("EVENT#"):
        raise EventStateError("Stored event_pk must use the EVENT# prefix.")

    event_id = event_pk.removeprefix("EVENT#")
    if not event_id:
        raise EventStateError("Stored event_pk must contain a public identifier.")

    return event_id


def _to_rsvp_event_id(attribute_value: Any) -> str:
    event_pk = _deserialize_rsvp_required_string(attribute_value, field_name="event_pk")
    if not event_pk.startswith("EVENT#"):
        raise RsvpStateError("Stored event_pk must use the EVENT# prefix.")

    event_id = event_pk.removeprefix("EVENT#")
    if not event_id:
        raise RsvpStateError("Stored event_pk must contain a public identifier.")

    return event_id


def _deserialize_event_status(attribute_value: Any) -> str:
    status = _deserialize_event_required_string(attribute_value, field_name="status")
    if status == "ACTIVE":
        return "ACTIVE"
    if status == "CANCELLED":
        return "CANCELLED"
    raise EventStateError("Stored status must be ACTIVE or CANCELLED.")


def _deserialize_event_date(attribute_value: Any) -> datetime:
    iso_date = _deserialize_event_required_string(attribute_value, field_name="date")
    try:
        parsed = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EventStateError("Stored date must be a valid ISO 8601 UTC timestamp.") from exc

    if parsed.tzinfo is None:
        raise EventStateError("Stored date must be a timezone-aware UTC timestamp.")
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise EventStateError("Stored date must be a canonical UTC timestamp.")

    return parsed.astimezone(timezone.utc)


def _deserialize_event_required_string(attribute_value: Any, *, field_name: str) -> str:
    if not isinstance(attribute_value, dict):
        raise EventStateError(f"Stored {field_name} must be a DynamoDB attribute object.")
    if "S" not in attribute_value or not isinstance(attribute_value["S"], str):
        raise EventStateError(f"Stored {field_name} must be a string.")

    value = attribute_value["S"].strip() if field_name in {"event_pk", "status"} else attribute_value["S"]
    if field_name in {"event_pk", "status"} and not value:
        raise EventStateError(f"Stored {field_name} must not be empty.")
    return value


def _deserialize_rsvp_required_string(attribute_value: Any, *, field_name: str) -> str:
    if not isinstance(attribute_value, dict):
        raise RsvpStateError(f"Stored {field_name} must be a DynamoDB attribute object.")
    if "S" not in attribute_value or not isinstance(attribute_value["S"], str):
        raise RsvpStateError(f"Stored {field_name} must be a string.")

    value = attribute_value["S"].strip() if field_name in {"event_pk", "subject_sk"} else attribute_value["S"]
    if field_name in {"event_pk", "subject_sk"} and not value:
        raise RsvpStateError(f"Stored {field_name} must not be empty.")
    return value


def _deserialize_rsvp_optional_string(attribute_value: Any, *, field_name: str) -> str | None:
    if attribute_value is None:
        return None
    if not isinstance(attribute_value, dict):
        raise RsvpStateError(f"Stored {field_name} must be a DynamoDB attribute object.")
    if "S" not in attribute_value or not isinstance(attribute_value["S"], str):
        raise RsvpStateError(f"Stored {field_name} must be a string.")
    return attribute_value["S"]


def _deserialize_event_bool(attribute_value: Any, *, field_name: str) -> bool:
    if not isinstance(attribute_value, dict):
        raise EventStateError(f"Stored {field_name} must be a DynamoDB attribute object.")
    if "BOOL" not in attribute_value or not isinstance(attribute_value["BOOL"], bool):
        raise EventStateError(f"Stored {field_name} must be a boolean.")
    return attribute_value["BOOL"]


def _deserialize_rsvp_bool(attribute_value: Any, *, field_name: str) -> bool:
    if not isinstance(attribute_value, dict):
        raise RsvpStateError(f"Stored {field_name} must be a DynamoDB attribute object.")
    if "BOOL" not in attribute_value or not isinstance(attribute_value["BOOL"], bool):
        raise RsvpStateError(f"Stored {field_name} must be a boolean.")
    return attribute_value["BOOL"]


def _deserialize_event_number(attribute_value: Any, *, field_name: str) -> int:
    if not isinstance(attribute_value, dict):
        raise EventStateError(f"Stored {field_name} must be a DynamoDB attribute object.")
    if "N" not in attribute_value or not isinstance(attribute_value["N"], str):
        raise EventStateError(f"Stored {field_name} must be an integer.")

    try:
        numeric_value = Decimal(attribute_value["N"])
    except Exception as exc:
        raise EventStateError(f"Stored {field_name} must be an integer.") from exc

    if numeric_value % 1 != 0:
        raise EventStateError(f"Stored {field_name} must be an integer.")
    return int(numeric_value)


def _deserialize_event_optional_number(attribute_value: Any, *, field_name: str) -> int | None:
    if attribute_value is None:
        return None
    if not isinstance(attribute_value, dict):
        raise EventStateError(f"Stored {field_name} must be an integer or null.")
    if attribute_value.get("NULL") is True:
        return None
    return _deserialize_event_number(attribute_value, field_name=field_name)


def _to_iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _get_dynamodb_client():
    return boto3.client("dynamodb")


def _get_required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} environment variable is required.")
    return value


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
