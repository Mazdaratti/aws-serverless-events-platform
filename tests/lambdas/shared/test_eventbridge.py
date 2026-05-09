import json
from unittest.mock import Mock

import pytest

from lambdas.shared.eventbridge import EventBridgePublishError, publish_domain_event


def test_publish_domain_event_builds_single_put_events_entry():
    eventbridge_client = Mock()
    eventbridge_client.put_events.return_value = {
        "FailedEntryCount": 0,
        "Entries": [{"EventId": "event-id-1"}],
    }

    publish_domain_event(
        eventbridge_client=eventbridge_client,
        event_bus_name="example-bus",
        source="aws-serverless-events-platform",
        detail_type="event.cancelled",
        detail={
            "event_id": "event-1",
            "title": "Platform Launch",
            "actor_user_id": "alice",
            "occurred_at": "2026-05-09T10:00:00Z",
            "event_detail_path": "/app/events/event-1",
        },
    )

    eventbridge_client.put_events.assert_called_once_with(
        Entries=[
            {
                "Source": "aws-serverless-events-platform",
                "DetailType": "event.cancelled",
                "Detail": (
                    '{"actor_user_id":"alice",'
                    '"event_detail_path":"/app/events/event-1",'
                    '"event_id":"event-1",'
                    '"occurred_at":"2026-05-09T10:00:00Z",'
                    '"title":"Platform Launch"}'
                ),
                "EventBusName": "example-bus",
            }
        ]
    )


def test_publish_domain_event_serializes_detail_as_json():
    eventbridge_client = Mock()
    eventbridge_client.put_events.return_value = {
        "FailedEntryCount": 0,
        "Entries": [{"EventId": "event-id-1"}],
    }

    publish_domain_event(
        eventbridge_client=eventbridge_client,
        event_bus_name="example-bus",
        source="aws-serverless-events-platform",
        detail_type="event.cancelled",
        detail={"z": "last", "a": "first"},
    )

    entry = eventbridge_client.put_events.call_args.kwargs["Entries"][0]
    assert json.loads(entry["Detail"]) == {"a": "first", "z": "last"}
    assert entry["Detail"] == '{"a":"first","z":"last"}'


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        ("event_bus_name", {"event_bus_name": ""}),
        ("event_bus_name", {"event_bus_name": "   "}),
        ("event_bus_name", {"event_bus_name": None}),
        ("source", {"source": ""}),
        ("detail_type", {"detail_type": ""}),
    ],
)
def test_publish_domain_event_rejects_blank_required_text(field_name, kwargs):
    eventbridge_client = Mock()
    base_kwargs = {
        "eventbridge_client": eventbridge_client,
        "event_bus_name": "example-bus",
        "source": "aws-serverless-events-platform",
        "detail_type": "event.cancelled",
        "detail": {"event_id": "event-1"},
    }
    base_kwargs.update(kwargs)

    with pytest.raises(ValueError, match=rf"{field_name} must be a non-empty string\."):
        publish_domain_event(**base_kwargs)

    eventbridge_client.put_events.assert_not_called()


def test_publish_domain_event_raises_when_eventbridge_reports_failed_entries():
    eventbridge_client = Mock()
    eventbridge_client.put_events.return_value = {
        "FailedEntryCount": 1,
        "Entries": [
            {
                "ErrorCode": "InternalFailure",
                "ErrorMessage": "EventBridge could not process this entry.",
            }
        ],
    }

    with pytest.raises(
        EventBridgePublishError,
        match=(
            "EventBridge failed to publish domain event "
            "failed_entry_count=1 error_code=InternalFailure "
            "error_message=EventBridge could not process this entry."
        ),
    ):
        publish_domain_event(
            eventbridge_client=eventbridge_client,
            event_bus_name="example-bus",
            source="aws-serverless-events-platform",
            detail_type="event.cancelled",
            detail={"event_id": "event-1"},
        )
