import json
from unittest.mock import Mock

import pytest

from lambdas.create_event import handler


@pytest.fixture
def mock_table(monkeypatch):
    # Replace the real DynamoDB resource with a mock so the tests validate
    # handler behavior without making any AWS calls.
    table = Mock()

    monkeypatch.setenv("EVENTS_TABLE_NAME", "example-events")
    monkeypatch.setattr(handler, "_get_dynamodb_table", lambda _table_name: table)

    return table


def test_lambda_handler_returns_created_response_for_direct_payload(monkeypatch, mock_table):
    # Freeze the generated ID and timestamp so the response and DynamoDB item
    # shape can be asserted deterministically.
    monkeypatch.setattr(handler.uuid, "uuid4", lambda: "12345678-1234-1234-1234-123456789abc")
    monkeypatch.setattr(handler, "_utc_now_iso8601", lambda: "2026-03-31T12:00:00Z")

    response = handler.lambda_handler(
        {
            "title": "Platform Launch Event",
            "date": "2026-06-15",
            "description": "Kickoff for the new platform.",
            "location": "Berlin",
            "capacity": 50,
            "creator_id": "alice",
        },
        None,
    )

    assert response["statusCode"] == 201
    assert response["headers"] == {"Content-Type": "application/json"}

    body = json.loads(response["body"])
    assert body == {
        "message": "Event created successfully.",
        "event_pk": "EVENT#12345678-1234-1234-1234-123456789abc",
        "date": "2026-06-15T00:00:00Z",
        "created_at": "2026-03-31T12:00:00Z",
    }

    mock_table.put_item.assert_called_once()
    item = mock_table.put_item.call_args.kwargs["Item"]

    assert item == {
        "event_pk": "EVENT#12345678-1234-1234-1234-123456789abc",
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


def test_lambda_handler_accepts_body_wrapped_json(monkeypatch, mock_table):
    # This mirrors the future API Gateway shape where the Lambda receives a
    # JSON string under "body" instead of a plain top-level payload.
    monkeypatch.setattr(handler.uuid, "uuid4", lambda: "aaaaaaaa-1234-1234-1234-aaaaaaaaaaaa")
    monkeypatch.setattr(handler, "_utc_now_iso8601", lambda: "2026-03-31T12:00:00Z")

    response = handler.lambda_handler(
        {
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
    assert item["date"] == "2026-06-15T16:30:00Z"
    assert item["is_public"] is False
    assert item["requires_admin"] is True
    assert item["description"] == ""
    assert item["location"] == ""
    assert item["creator_id"] == "anonymous"
    assert "public_upcoming_gsi_pk" not in item
    assert "public_upcoming_gsi_sk" not in item


def test_lambda_handler_returns_400_when_title_is_missing(mock_table):
    # Validation failures should not write anything to DynamoDB.
    response = handler.lambda_handler({"date": "2026-06-15"}, None)

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "title is required and must not be empty."
    }
    mock_table.put_item.assert_not_called()


def test_lambda_handler_returns_400_when_date_is_invalid(mock_table):
    response = handler.lambda_handler(
        {
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
