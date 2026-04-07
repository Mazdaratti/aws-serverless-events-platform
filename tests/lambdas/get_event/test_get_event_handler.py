import json
from decimal import Decimal
from unittest.mock import Mock

import pytest

from lambdas.get_event import handler


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


def test_lambda_handler_returns_public_event_dto_for_direct_invocation(mock_table):
    # The simplest current invocation shape passes the public event_id directly
    # at the top level.
    mock_table.get_item.return_value = {
        "Item": _valid_item()
    }

    response = handler.lambda_handler(
        {"event_id": "11111111-1111-1111-1111-111111111111"},
        None,
    )

    assert response["statusCode"] == 200
    assert response["headers"] == {"Content-Type": "application/json"}

    # The Lambda returns the standard API Gateway-style wrapper, so the useful
    # business payload lives inside the JSON string stored in "body".
    body = json.loads(response["body"])
    assert body == {
        "item": {
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
    }
    assert "event_pk" not in body["item"]

    mock_table.get_item.assert_called_once_with(
        Key={"event_pk": "EVENT#11111111-1111-1111-1111-111111111111"}
    )


def test_lambda_handler_accepts_api_gateway_path_parameters(mock_table):
    # This mirrors the future API Gateway route shape where the event ID comes
    # from a path parameter rather than a top-level direct-invoke field.
    mock_table.get_item.return_value = {
        "Item": _valid_item(
            event_pk="EVENT#22222222-2222-2222-2222-222222222222",
            title="Private Planning Session",
            date="2026-07-01T00:00:00Z",
            description="",
            location="",
            capacity=None,
            is_public=False,
            rsvp_total=Decimal("0"),
            attending_count=Decimal("0"),
            not_attending_count=Decimal("0"),
        )
    }

    response = handler.lambda_handler(
        {
            "pathParameters": {
                "event_id": "22222222-2222-2222-2222-222222222222",
            }
        },
        None,
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "item": {
            "event_id": "22222222-2222-2222-2222-222222222222",
            "status": "ACTIVE",
            "title": "Private Planning Session",
            "date": "2026-07-01T00:00:00Z",
            "description": "",
            "location": "",
            "capacity": None,
            "is_public": False,
            "requires_admin": False,
            "created_by": "alice",
            "created_at": "2026-03-31T12:00:00Z",
            "rsvp_count": 0,
            "attending_count": 0,
        }
    }


def test_lambda_handler_prefers_path_parameters_over_top_level_event_id(mock_table):
    # When both shapes are present, pathParameters should win so the handler
    # already aligns with the future route-driven API Gateway contract.
    mock_table.get_item.return_value = {
        "Item": _valid_item(
            event_pk="EVENT#33333333-3333-3333-3333-333333333333",
            title="Ownership Check",
            date="2026-09-20T00:00:00Z",
            description="",
            location="",
            capacity=None,
            rsvp_total=Decimal("0"),
            attending_count=Decimal("0"),
            not_attending_count=Decimal("0"),
        )
    }

    response = handler.lambda_handler(
        {
            "event_id": "top-level-id-should-not-be-used",
            "pathParameters": {
                "event_id": "33333333-3333-3333-3333-333333333333",
            },
        },
        None,
    )

    assert response["statusCode"] == 200
    mock_table.get_item.assert_called_once_with(
        Key={"event_pk": "EVENT#33333333-3333-3333-3333-333333333333"}
    )


def test_lambda_handler_returns_400_for_non_dict_event_payload(mock_table):
    response = handler.lambda_handler("not-a-dict", None)

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "Event payload must be a JSON object."
    }
    mock_table.get_item.assert_not_called()


def test_lambda_handler_returns_400_when_event_id_is_missing(mock_table):
    response = handler.lambda_handler({}, None)

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "event_id is required."
    }
    mock_table.get_item.assert_not_called()


def test_lambda_handler_returns_400_when_event_id_is_blank(mock_table):
    response = handler.lambda_handler({"event_id": "   "}, None)

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "event_id must be a non-empty string."
    }
    mock_table.get_item.assert_not_called()


def test_lambda_handler_returns_400_when_event_id_is_not_a_string(mock_table):
    response = handler.lambda_handler({"event_id": 123}, None)

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "event_id must be a non-empty string."
    }
    mock_table.get_item.assert_not_called()


def test_lambda_handler_returns_400_when_event_id_uses_internal_storage_key(mock_table):
    response = handler.lambda_handler({"event_id": "EVENT#abc"}, None)

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "event_id must use the public identifier, not the internal storage key."
    }
    mock_table.get_item.assert_not_called()


def test_lambda_handler_returns_400_when_path_parameters_is_not_an_object(mock_table):
    response = handler.lambda_handler({"pathParameters": "not-an-object"}, None)

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "pathParameters must be an object when provided."
    }
    mock_table.get_item.assert_not_called()


def test_lambda_handler_returns_404_when_event_does_not_exist(mock_table):
    # Missing items are a normal single-record read outcome and should return
    # a business-level 404 instead of a 500.
    mock_table.get_item.return_value = {}

    response = handler.lambda_handler(
        {"event_id": "44444444-4444-4444-4444-444444444444"},
        None,
    )

    assert response["statusCode"] == 404
    assert json.loads(response["body"]) == {
        "message": "Event not found."
    }


def test_lambda_handler_returns_500_when_dynamodb_item_is_not_an_object(mock_table):
    mock_table.get_item.return_value = {"Item": "not-a-dict"}

    response = handler.lambda_handler(
        {"event_id": "45454545-4545-4545-4545-454545454545"},
        None,
    )

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {
        "message": "Internal server error."
    }


def test_lambda_handler_returns_500_for_invalid_stored_event_key_shape(mock_table):
    # Bad stored data should be treated as an internal failure, not as a bad
    # request from the caller.
    mock_table.get_item.return_value = {
        "Item": _valid_item(event_pk="bad-storage-key")
    }

    response = handler.lambda_handler(
        {"event_id": "55555555-5555-5555-5555-555555555555"},
        None,
    )

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {
        "message": "Internal server error."
    }


def test_lambda_handler_returns_500_for_invalid_stored_text_field_type(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(title=["unexpected-list-value"])
    }

    response = handler.lambda_handler(
        {"event_id": "66666666-6666-6666-6666-666666666666"},
        None,
    )

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {
        "message": "Internal server error."
    }


def test_lambda_handler_returns_500_for_missing_stored_status(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(status=None)
    }

    response = handler.lambda_handler(
        {"event_id": "67676767-6767-6767-6767-676767676767"},
        None,
    )

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {
        "message": "Internal server error."
    }


def test_lambda_handler_returns_cancelled_status_in_public_dto(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(status="CANCELLED")
    }

    response = handler.lambda_handler(
        {"event_id": "78787878-7878-7878-7878-787878787878"},
        None,
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["item"]["status"] == "CANCELLED"


def test_lambda_handler_returns_500_for_invalid_stored_boolean_field(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(is_public="true")
    }

    response = handler.lambda_handler(
        {"event_id": "77777777-7777-7777-7777-777777777777"},
        None,
    )

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {
        "message": "Internal server error."
    }


def test_lambda_handler_returns_500_for_non_integral_decimal_capacity(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(capacity=Decimal("10.5"))
    }

    response = handler.lambda_handler(
        {"event_id": "88888888-8888-8888-8888-888888888888"},
        None,
    )

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {
        "message": "Internal server error."
    }
