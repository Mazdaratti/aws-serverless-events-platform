from __future__ import annotations

import json
from typing import Any


class EventBridgePublishError(RuntimeError):
    """Raised when EventBridge reports a failed event publication."""


def publish_domain_event(
    *,
    eventbridge_client: Any,
    event_bus_name: str,
    source: str,
    detail_type: str,
    detail: dict[str, Any],
) -> None:
    """Publish one compact domain event to EventBridge."""
    bus_name = _normalize_required_text(event_bus_name, field_name="event_bus_name")
    event_source = _normalize_required_text(source, field_name="source")
    event_detail_type = _normalize_required_text(detail_type, field_name="detail_type")

    response = eventbridge_client.put_events(
        Entries=[
            {
                "Source": event_source,
                "DetailType": event_detail_type,
                "Detail": json.dumps(detail, separators=(",", ":"), sort_keys=True),
                "EventBusName": bus_name,
            }
        ]
    )

    failed_entry_count = response.get("FailedEntryCount", 0)
    if failed_entry_count:
        entries = response.get("Entries", [])
        error_code = _first_failed_entry_value(entries, "ErrorCode")
        error_message = _first_failed_entry_value(entries, "ErrorMessage")
        raise EventBridgePublishError(
            "EventBridge failed to publish domain event"
            f" failed_entry_count={failed_entry_count}"
            f" error_code={error_code or 'unknown'}"
            f" error_message={error_message or 'unknown'}"
        )


def _normalize_required_text(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string.")

    candidate = value.strip()
    if not candidate:
        raise ValueError(f"{field_name} must be a non-empty string.")

    return candidate


def _first_failed_entry_value(entries: Any, key: str) -> str | None:
    if not isinstance(entries, list):
        return None

    for entry in entries:
        if isinstance(entry, dict) and entry.get(key):
            return str(entry[key])

    return None
