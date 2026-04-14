import base64
import json
from decimal import Decimal
from unittest.mock import Mock

import pytest

from lambdas.list_my_events import handler


def _valid_item(**overrides) -> dict[str, object]:
    item: dict[str, object] = {
        "event_pk": "EVENT#11111111-1111-1111-1111-111111111111",
        "status": "ACTIVE",
        "title": "Platform Launch Event",
        "date": "2026-06-15T00:00:00Z",
        "description": "Kickoff for the new platform.",
        "location": "Berlin",
        "capacity": Decimal("50"),
        "is_public": True,
        "requires_admin": False,
        "creator_id": "alice",
        "created_at": "2026-03-31T12:00:00Z",
        "rsvp_total": Decimal("3"),
        "attending_count": Decimal("2"),
        "not_attending_count": Decimal("1"),
        "creator_events_gsi_pk": "CREATOR#alice",
        "creator_events_gsi_sk": "2026-06-15T00:00:00Z#11111111-1111-1111-1111-111111111111",
    }
    item.update(overrides)
    return item


def _authenticated_event(*, user_id: str = "alice", limit: object | None = None, next_cursor: object | None = None) -> dict[str, object]:
    event: dict[str, object] = {
        "caller": {
            "user_id": user_id,
            "is_authenticated": True,
            "is_admin": False,
        }
    }

    if limit is not None:
        event["limit"] = limit
    if next_cursor is not None:
        event["next_cursor"] = next_cursor

    return event


@pytest.fixture
def mock_table(monkeypatch):
    table = Mock()

    monkeypatch.setenv("EVENTS_TABLE_NAME", "example-events")
    monkeypatch.setattr(handler, "_get_dynamodb_table", lambda _table_name: table)

    return table


def test_lambda_handler_returns_creator_scoped_event_dtos(mock_table):
    mock_table.query.return_value = {
        "Items": [
            _valid_item(),
        ]
    }

    response = handler.lambda_handler(_authenticated_event(user_id="alice"), None)

    assert response["statusCode"] == 200
    assert response["headers"] == {"Content-Type": "application/json"}

    body = json.loads(response["body"])
    assert body == {
        "items": [
            {
                "event_id": "11111111-1111-1111-1111-111111111111",
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
                "rsvp_count": 3,
                "attending_count": 2,
            }
        ],
        "next_cursor": None,
    }

    mock_table.query.assert_called_once()
    query_kwargs = mock_table.query.call_args.kwargs
    assert query_kwargs["IndexName"] == "creator-events"
    assert query_kwargs["Limit"] == 20


def test_lambda_handler_returns_empty_list_when_creator_has_no_events(mock_table):
    mock_table.query.return_value = {"Items": []}

    response = handler.lambda_handler(_authenticated_event(user_id="alice"), None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "items": [],
        "next_cursor": None,
    }
    mock_table.query.assert_called_once()


def test_lambda_handler_accepts_query_string_parameters(mock_table):
    mock_table.query.return_value = {"Items": []}

    response = handler.lambda_handler(
        {
            "caller": {
                "user_id": "alice",
                "is_authenticated": True,
                "is_admin": False,
            },
            "queryStringParameters": {
                "limit": "5",
            },
        },
        None,
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "items": [],
        "next_cursor": None,
    }
    mock_table.query.assert_called_once()
    assert mock_table.query.call_args.kwargs["Limit"] == 5


def test_lambda_handler_requires_authenticated_caller(mock_table):
    response = handler.lambda_handler({}, None)

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "Authenticated caller context is required."
    }
    mock_table.query.assert_not_called()


def test_lambda_handler_includes_cancelled_events_for_creator(mock_table):
    mock_table.query.return_value = {
        "Items": [
            _valid_item(
                event_pk="EVENT#22222222-2222-2222-2222-222222222222",
                status="CANCELLED",
                title="Cancelled Planning Session",
            )
        ]
    }

    response = handler.lambda_handler(_authenticated_event(user_id="alice"), None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["next_cursor"] is None
    assert body["items"][0]["event_id"] == "22222222-2222-2222-2222-222222222222"
    assert body["items"][0]["status"] == "CANCELLED"


def test_lambda_handler_uses_and_returns_opaque_cursor_for_pagination(mock_table):
    incoming_cursor_payload = {
        "event_pk": "EVENT#11111111-1111-1111-1111-111111111111",
        "creator_events_gsi_pk": "CREATOR#alice",
        "creator_events_gsi_sk": "2026-06-15T00:00:00Z#11111111-1111-1111-1111-111111111111",
    }
    incoming_cursor = base64.urlsafe_b64encode(
        json.dumps(incoming_cursor_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("utf-8").rstrip("=")

    last_evaluated_key = {
        "event_pk": "EVENT#33333333-3333-3333-3333-333333333333",
        "creator_events_gsi_pk": "CREATOR#alice",
        "creator_events_gsi_sk": "2026-07-01T00:00:00Z#33333333-3333-3333-3333-333333333333",
    }
    expected_outgoing_cursor = base64.urlsafe_b64encode(
        json.dumps(last_evaluated_key, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("utf-8").rstrip("=")

    mock_table.query.return_value = {
        "Items": [],
        "LastEvaluatedKey": last_evaluated_key,
    }

    response = handler.lambda_handler(
        _authenticated_event(user_id="alice", next_cursor=incoming_cursor),
        None,
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "items": [],
        "next_cursor": expected_outgoing_cursor,
    }
    mock_table.query.assert_called_once()
    query_kwargs = mock_table.query.call_args.kwargs
    assert query_kwargs["ExclusiveStartKey"] == incoming_cursor_payload


def test_lambda_handler_returns_400_for_invalid_limit(mock_table):
    response = handler.lambda_handler(_authenticated_event(user_id="alice", limit="abc"), None)

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "limit must be an integer between 1 and 100."
    }
    mock_table.query.assert_not_called()


def test_lambda_handler_returns_400_for_invalid_cursor(mock_table):
    response = handler.lambda_handler(
        _authenticated_event(user_id="alice", next_cursor="%%%not-a-valid-cursor%%%"),
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "next_cursor must be a valid opaque cursor."
    }
    mock_table.query.assert_not_called()


def test_lambda_handler_returns_500_when_items_payload_is_not_a_list(mock_table):
    mock_table.query.return_value = {
        "Items": "not-a-list",
    }

    response = handler.lambda_handler(_authenticated_event(user_id="alice"), None)

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {
        "message": "Internal server error."
    }


def test_lambda_handler_returns_500_for_invalid_stored_status(mock_table):
    mock_table.query.return_value = {
        "Items": [_valid_item(status="ARCHIVED")],
    }

    response = handler.lambda_handler(_authenticated_event(user_id="alice"), None)

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {
        "message": "Internal server error."
    }
