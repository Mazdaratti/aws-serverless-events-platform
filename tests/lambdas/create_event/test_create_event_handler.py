import json
from unittest.mock import Mock

import pytest

from lambdas.create_event import handler
from lambdas.shared.eventbridge import EventBridgePublishError


def _authenticated_event(*, user_id: str = "alice", is_admin: bool = False) -> dict[str, object]:
    # Use the normalized synthetic caller test shape supported by the shared
    # auth helper so handler tests stay decoupled from any one raw authorizer
    # event layout.
    return {
        "caller": {
            "user_id": user_id,
            "is_authenticated": True,
            "is_admin": is_admin,
        }
    }


@pytest.fixture
def mock_table(monkeypatch):
    # Replace the real DynamoDB resource with a mock so the tests validate
    # handler behavior without making any AWS calls.
    table = Mock()

    monkeypatch.setenv("EVENTS_TABLE_NAME", "example-events")
    monkeypatch.setattr(handler, "_get_dynamodb_table", lambda _table_name: table)

    return table


@pytest.fixture
def mock_eventbridge_publish(monkeypatch):
    eventbridge_client = Mock()
    publish = Mock()

    monkeypatch.setenv("EVENTBRIDGE_EVENT_BUS_NAME", "example-event-bus")
    monkeypatch.setattr(handler, "_get_eventbridge_client", lambda: eventbridge_client)
    monkeypatch.setattr(handler, "publish_domain_event", publish)

    return publish, eventbridge_client


def test_lambda_handler_returns_created_response_for_direct_payload(
    monkeypatch,
    mock_table,
    mock_eventbridge_publish,
):
    publish, _eventbridge_client = mock_eventbridge_publish
    # Freeze the generated ID and timestamp so the response and DynamoDB item
    # shape can be asserted deterministically.
    monkeypatch.setattr(handler.uuid, "uuid4", lambda: "12345678-1234-1234-1234-123456789abc")
    monkeypatch.setattr(handler, "_utc_now_iso8601", lambda: "2026-03-31T12:00:00Z")

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "title": "Platform Launch Event",
            "date": "2026-06-15",
            "description": "Kickoff for the new platform.",
            "location": "Berlin",
            "capacity": 50,
        },
        None,
    )

    assert response["statusCode"] == 201
    assert response["headers"] == {"Content-Type": "application/json"}

    # The handler returns an API Gateway-style wrapper, so the business payload
    # lives inside the JSON string stored in "body".
    body = json.loads(response["body"])
    assert body == {
        "item": {
            "event_id": "12345678-1234-1234-1234-123456789abc",
            "status": "ACTIVE",
            "title": "Platform Launch Event",
            "date": "2026-06-15T00:00:00Z",
            "description": "Kickoff for the new platform.",
            "location": "Berlin",
            "capacity": 50,
            "is_public": True,
            "requires_admin": False,
            "created_by": "alice",
            "created_at": "2026-03-31T12:00:00Z",
            "rsvp_count": 0,
            "attending_count": 0,
        }
    }
    assert "event_pk" not in body["item"]

    mock_table.put_item.assert_called_once()
    item = mock_table.put_item.call_args.kwargs["Item"]

    # This assertion checks the full canonical DynamoDB item shape expected for
    # a normal public event creation path.
    assert item == {
        "event_pk": "EVENT#12345678-1234-1234-1234-123456789abc",
        "status": "ACTIVE",
        "title": "Platform Launch Event",
        "date": "2026-06-15T00:00:00Z",
        "description": "Kickoff for the new platform.",
        "location": "Berlin",
        "capacity": 50,
        "is_public": True,
        "requires_admin": False,
        "creator_id": "alice",
        "created_at": "2026-03-31T12:00:00Z",
        "rsvp_total": 0,
        "attending_count": 0,
        "not_attending_count": 0,
        "creator_events_gsi_pk": "CREATOR#alice",
        "creator_events_gsi_sk": "2026-06-15T00:00:00Z#12345678-1234-1234-1234-123456789abc",
        "public_upcoming_gsi_pk": "PUBLIC",
        "public_upcoming_gsi_sk": "2026-06-15T00:00:00Z#12345678-1234-1234-1234-123456789abc",
    }
    publish.assert_called_once()


def test_lambda_handler_accepts_body_wrapped_json(monkeypatch, mock_table, mock_eventbridge_publish):
    # This mirrors the API Gateway shape where the Lambda receives a JSON
    # string under "body" instead of a plain top-level payload.
    monkeypatch.setattr(handler.uuid, "uuid4", lambda: "aaaaaaaa-1234-1234-1234-aaaaaaaaaaaa")
    monkeypatch.setattr(handler, "_utc_now_iso8601", lambda: "2026-03-31T12:00:00Z")

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice", is_admin=True),
            "body": json.dumps(
                {
                    "title": "Private Planning Session",
                    "date": "2026-06-15T18:30:00+02:00",
                    "is_public": False,
                    "requires_admin": True,
                }
            )
        },
        None,
    )

    assert response["statusCode"] == 201

    item = mock_table.put_item.call_args.kwargs["Item"]
    # Private events should still be created successfully, but they must stay
    # out of the public upcoming-events index.
    body = json.loads(response["body"])
    assert body["item"]["status"] == "ACTIVE"
    assert item["date"] == "2026-06-15T16:30:00Z"
    assert item["status"] == "ACTIVE"
    assert item["is_public"] is False
    assert item["requires_admin"] is True
    assert item["description"] == ""
    assert item["location"] == ""
    assert item["creator_id"] == "alice"
    assert "public_upcoming_gsi_pk" not in item
    assert "public_upcoming_gsi_sk" not in item


def test_lambda_handler_publishes_event_created_after_successful_create(
    monkeypatch,
    mock_table,
    mock_eventbridge_publish,
):
    publish, eventbridge_client = mock_eventbridge_publish
    monkeypatch.setattr(handler.uuid, "uuid4", lambda: "dddddddd-1234-1234-1234-dddddddddddd")
    monkeypatch.setattr(handler, "_utc_now_iso8601", lambda: "2026-05-10T10:00:00Z")

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "title": "EventBridge Created Validation",
            "date": "2026-09-01T18:00:00Z",
        },
        None,
    )

    assert response["statusCode"] == 201
    mock_table.put_item.assert_called_once()
    publish.assert_called_once_with(
        eventbridge_client=eventbridge_client,
        event_bus_name="example-event-bus",
        source="aws-serverless-events-platform",
        detail_type="event.created",
        detail={
            "event_id": "dddddddd-1234-1234-1234-dddddddddddd",
            "title": "EventBridge Created Validation",
            "actor_user_id": "alice",
            "occurred_at": "2026-05-10T10:00:00Z",
            "event_detail_path": "/app/events/dddddddd-1234-1234-1234-dddddddddddd",
        },
    )


def test_lambda_handler_published_event_detail_uses_only_notification_safe_fields(
    monkeypatch,
    mock_table,
    mock_eventbridge_publish,
):
    publish, _eventbridge_client = mock_eventbridge_publish
    monkeypatch.setattr(handler.uuid, "uuid4", lambda: "eeeeeeee-1234-1234-1234-eeeeeeeeeeee")
    monkeypatch.setattr(handler, "_utc_now_iso8601", lambda: "2026-05-10T10:00:00Z")

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "title": "Safe Payload Check",
            "date": "2026-09-01T18:00:00Z",
            "description": "This should stay out of the EventBridge detail.",
            "location": "Berlin",
            "capacity": 20,
        },
        None,
    )

    assert response["statusCode"] == 201
    detail = publish.call_args.kwargs["detail"]
    assert set(detail) == {
        "event_id",
        "title",
        "actor_user_id",
        "occurred_at",
        "event_detail_path",
    }
    assert "email" not in detail
    assert "anonymous_token" not in detail
    assert "event_pk" not in detail
    assert "rsvps" not in detail
    assert "claims" not in detail
    assert "description" not in detail
    assert "location" not in detail


def test_lambda_handler_keeps_success_response_when_eventbridge_publish_fails(
    monkeypatch,
    mock_table,
    mock_eventbridge_publish,
):
    publish, _eventbridge_client = mock_eventbridge_publish
    publish.side_effect = EventBridgePublishError("put events failed")
    monkeypatch.setattr(handler.uuid, "uuid4", lambda: "ffffffff-1234-1234-1234-ffffffffffff")
    monkeypatch.setattr(handler, "_utc_now_iso8601", lambda: "2026-05-10T10:00:00Z")

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "title": "Publish Failure Still Creates Event",
            "date": "2026-09-01T18:00:00Z",
        },
        None,
    )

    assert response["statusCode"] == 201
    body = json.loads(response["body"])
    assert body["item"]["event_id"] == "ffffffff-1234-1234-1234-ffffffffffff"
    assert body["item"]["status"] == "ACTIVE"
    mock_table.put_item.assert_called_once()
    publish.assert_called_once()


def test_lambda_handler_returns_400_when_caller_context_is_missing(
    mock_table,
    mock_eventbridge_publish,
):
    publish, _eventbridge_client = mock_eventbridge_publish
    # Event creation is no longer anonymous. Missing caller context should fail
    # before any DynamoDB write is attempted.
    response = handler.lambda_handler(
        {
            "title": "Platform Launch Event",
            "date": "2026-06-15",
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "Authenticated caller context is required."
    }
    mock_table.put_item.assert_not_called()
    publish.assert_not_called()


def test_lambda_handler_returns_400_when_title_is_missing(mock_table, mock_eventbridge_publish):
    publish, _eventbridge_client = mock_eventbridge_publish
    # Validation failures should not write anything to DynamoDB.
    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "date": "2026-06-15",
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "title is required and must not be empty."
    }
    mock_table.put_item.assert_not_called()
    publish.assert_not_called()


def test_lambda_handler_returns_400_when_date_is_invalid(mock_table, mock_eventbridge_publish):
    publish, _eventbridge_client = mock_eventbridge_publish
    # Invalid dates should be rejected before normalization or persistence.
    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "title": "Broken Event",
            "date": "not-a-date",
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "date must use ISO 8601 format."
    }
    mock_table.put_item.assert_not_called()
    publish.assert_not_called()


def test_lambda_handler_does_not_publish_when_dynamodb_create_fails(
    monkeypatch,
    mock_table,
    mock_eventbridge_publish,
):
    publish, _eventbridge_client = mock_eventbridge_publish
    monkeypatch.setattr(handler.uuid, "uuid4", lambda: "99999999-1234-1234-1234-999999999999")
    monkeypatch.setattr(handler, "_utc_now_iso8601", lambda: "2026-05-10T10:00:00Z")
    mock_table.put_item.side_effect = RuntimeError("DynamoDB write failed")

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "title": "Failed Create",
            "date": "2026-09-01T18:00:00Z",
        },
        None,
    )

    assert response["statusCode"] == 500
    publish.assert_not_called()


def test_lambda_handler_ignores_request_body_creator_id(
    monkeypatch,
    mock_table,
    mock_eventbridge_publish,
):
    # A client must not be able to spoof event ownership by sending a different
    # creator_id in the request body.
    monkeypatch.setattr(handler.uuid, "uuid4", lambda: "bbbbbbbb-1234-1234-1234-bbbbbbbbbbbb")
    monkeypatch.setattr(handler, "_utc_now_iso8601", lambda: "2026-03-31T12:00:00Z")

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "title": "Ownership Check",
            "date": "2026-08-01",
            "creator_id": "mallory",
        },
        None,
    )

    assert response["statusCode"] == 201

    item = mock_table.put_item.call_args.kwargs["Item"]
    body = json.loads(response["body"])
    assert body["item"]["status"] == "ACTIVE"
    assert body["item"]["created_by"] == "alice"
    assert item["creator_id"] == "alice"
    assert item["status"] == "ACTIVE"
    assert item["creator_events_gsi_pk"] == "CREATOR#alice"


def test_lambda_handler_returns_400_for_admin_only_event_without_admin_role(
    mock_table,
    mock_eventbridge_publish,
):
    publish, _eventbridge_client = mock_eventbridge_publish
    # Admin-only event creation is a business authorization rule enforced
    # inside the Lambda after caller identity has already been resolved.
    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice", is_admin=False),
            "title": "Security Review",
            "date": "2026-08-15",
            "is_public": False,
            "requires_admin": True,
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "admin privileges are required to create admin-only events."
    }
    mock_table.put_item.assert_not_called()
    publish.assert_not_called()


def test_lambda_handler_allows_admin_only_event_for_admin(
    monkeypatch,
    mock_table,
    mock_eventbridge_publish,
):
    # The positive-path pair for the rule above: an admin caller may create an
    # admin-only event successfully.
    monkeypatch.setattr(handler.uuid, "uuid4", lambda: "cccccccc-1234-1234-1234-cccccccccccc")
    monkeypatch.setattr(handler, "_utc_now_iso8601", lambda: "2026-03-31T12:00:00Z")

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="admin-user", is_admin=True),
            "title": "Security Review",
            "date": "2026-08-15",
            "is_public": False,
            "requires_admin": True,
        },
        None,
    )

    assert response["statusCode"] == 201

    item = mock_table.put_item.call_args.kwargs["Item"]
    body = json.loads(response["body"])
    assert body["item"]["status"] == "ACTIVE"
    assert body["item"]["created_by"] == "admin-user"
    assert item["creator_id"] == "admin-user"
    assert item["status"] == "ACTIVE"
    assert item["requires_admin"] is True
    assert item["is_public"] is False
