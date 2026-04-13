import base64
import json
from decimal import Decimal
from unittest.mock import Mock

import pytest

from lambdas.list_events import handler


def _valid_item(**overrides) -> dict[str, object]:
    # Keep one canonical stored DynamoDB event shape in the test file so each
    # test can override only the field it actually cares about.
    item: dict[str, object] = {
        "event_pk": "EVENT#11111111-1111-1111-1111-111111111111",
        "status": "ACTIVE",
        "title": "Platform Launch Event",
        "date": "2026-06-15T00:00:00Z",
        "description": "Kickoff for the new platform.",
        "location": "Berlin",
        # Real DynamoDB number attributes come back through boto3 as Decimal
        # values, so the handler tests should mirror that behavior.
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
        "public_upcoming_gsi_pk": "PUBLIC",
        "public_upcoming_gsi_sk": "2026-06-15T00:00:00Z#11111111-1111-1111-1111-111111111111",
    }
    item.update(overrides)
    return item


@pytest.fixture
def mock_table(monkeypatch):
    # Replace the real DynamoDB resource with a mock so the tests validate
    # handler behavior without making any AWS calls.
    table = Mock()

    monkeypatch.setenv("EVENTS_TABLE_NAME", "example-events")
    monkeypatch.setattr(handler, "_get_dynamodb_table", lambda _table_name: table)

    return table


def test_lambda_handler_returns_public_event_dtos_for_default_all_mode(mock_table):
    # The default behavior should be the broad "all events" listing mode.
    mock_table.scan.return_value = {
        "Items": [
            _valid_item()
        ]
    }

    response = handler.lambda_handler({}, None)

    assert response["statusCode"] == 200
    assert response["headers"] == {"Content-Type": "application/json"}

    # The Lambda returns an API Gateway-style wrapper, so the useful business
    # payload lives inside the JSON string stored in "body".
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
    assert "event_pk" not in body["items"][0]

    mock_table.scan.assert_called_once_with(Limit=20)


def test_lambda_handler_accepts_query_string_parameters_for_all_mode(mock_table):
    # This mirrors the future API Gateway request shape where listing inputs
    # arrive as query-string values instead of top-level direct-invoke fields.
    mock_table.scan.return_value = {"Items": []}

    response = handler.lambda_handler(
        {
            "queryStringParameters": {
                "mode": "all",
                "limit": "5",
            }
        },
        None,
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "items": [],
        "next_cursor": None,
    }
    mock_table.scan.assert_called_once_with(Limit=5)


def test_lambda_handler_filters_cancelled_events_from_all_mode(mock_table):
    mock_table.scan.return_value = {
        "Items": [
            _valid_item(
                event_pk="EVENT#11111111-1111-1111-1111-111111111111",
                status="ACTIVE",
            ),
            _valid_item(
                event_pk="EVENT#22222222-2222-2222-2222-222222222222",
                status="CANCELLED",
                title="Cancelled Event",
            ),
        ]
    }

    response = handler.lambda_handler({"mode": "all"}, None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["next_cursor"] is None
    assert len(body["items"]) == 1
    assert body["items"][0]["event_id"] == "11111111-1111-1111-1111-111111111111"
    assert body["items"][0]["status"] == "ACTIVE"

def test_lambda_handler_returns_400_for_invalid_limit(mock_table):
    response = handler.lambda_handler({"limit": "abc"}, None)

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "limit must be an integer between 1 and 100."
    }
    mock_table.query.assert_not_called()
    mock_table.scan.assert_not_called()


def test_lambda_handler_returns_400_for_invalid_cursor(mock_table):
    response = handler.lambda_handler({"next_cursor": "%%%not-a-valid-cursor%%%"}, None)

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "next_cursor must be a valid opaque cursor."
    }
    mock_table.query.assert_not_called()
    mock_table.scan.assert_not_called()


def test_lambda_handler_uses_and_returns_opaque_cursor_for_pagination(mock_table):
    # The public API should see only an opaque cursor, even though internally
    # it represents DynamoDB LastEvaluatedKey state.
    incoming_cursor_payload = {
        "event_pk": "EVENT#11111111-1111-1111-1111-111111111111",
    }
    incoming_cursor = base64.urlsafe_b64encode(
        json.dumps(incoming_cursor_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("utf-8").rstrip("=")

    last_evaluated_key = {
        "event_pk": "EVENT#33333333-3333-3333-3333-333333333333",
    }
    expected_outgoing_cursor = base64.urlsafe_b64encode(
        json.dumps(last_evaluated_key, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("utf-8").rstrip("=")

    mock_table.scan.return_value = {
        "Items": [],
        "LastEvaluatedKey": last_evaluated_key,
    }

    response = handler.lambda_handler(
        {
            "mode": "all",
            "next_cursor": incoming_cursor,
        },
        None,
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "items": [],
        "next_cursor": expected_outgoing_cursor,
    }
    mock_table.scan.assert_called_once_with(
        Limit=20,
        ExclusiveStartKey=incoming_cursor_payload,
    )


def test_lambda_handler_returns_500_when_items_payload_is_not_a_list(mock_table):
    mock_table.scan.return_value = {
        "Items": "not-a-list",
    }

    response = handler.lambda_handler({}, None)

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {
        "message": "Internal server error."
    }


def test_lambda_handler_returns_500_when_a_returned_item_is_not_an_object(mock_table):
    mock_table.scan.return_value = {
        "Items": ["not-a-dict"],
    }

    response = handler.lambda_handler({}, None)

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {
        "message": "Internal server error."
    }


def test_lambda_handler_returns_500_for_invalid_stored_event_key_shape(mock_table):
    mock_table.scan.return_value = {
        "Items": [_valid_item(event_pk="bad-storage-key")],
    }

    response = handler.lambda_handler({}, None)

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {
        "message": "Internal server error."
    }


def test_lambda_handler_returns_500_for_invalid_stored_text_field_type(mock_table):
    mock_table.scan.return_value = {
        "Items": [_valid_item(title=["unexpected-list-value"])],
    }

    response = handler.lambda_handler({}, None)

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {
        "message": "Internal server error."
    }


def test_lambda_handler_returns_500_for_invalid_stored_boolean_field(mock_table):
    mock_table.scan.return_value = {
        "Items": [_valid_item(is_public="true")],
    }

    response = handler.lambda_handler({}, None)

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {
        "message": "Internal server error."
    }


def test_lambda_handler_returns_500_for_missing_stored_status_in_public_mode(mock_table):
    mock_table.scan.return_value = {
        "Items": [_valid_item(status=None)],
    }

    response = handler.lambda_handler({}, None)

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {
        "message": "Internal server error."
    }


def test_lambda_handler_returns_500_for_invalid_stored_status_in_all_mode(mock_table):
    mock_table.scan.return_value = {
        "Items": [_valid_item(status="ARCHIVED")],
    }

    response = handler.lambda_handler({}, None)

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {
        "message": "Internal server error."
    }


def test_lambda_handler_returns_500_for_non_integral_decimal_capacity(mock_table):
    mock_table.scan.return_value = {
        "Items": [_valid_item(capacity=Decimal("10.5"))],
    }

    response = handler.lambda_handler({}, None)

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {
        "message": "Internal server error."
    }
