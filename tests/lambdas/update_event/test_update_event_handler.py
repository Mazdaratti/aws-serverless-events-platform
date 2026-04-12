import json
from decimal import Decimal
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from lambdas.update_event import handler


def _authenticated_event(*, user_id: str = "alice", is_admin: bool = False) -> dict[str, object]:
    # Use the normalized synthetic caller test shape supported by the shared
    # auth helper so these tests stay focused on update-event business rules
    # instead of one raw authorizer transport format.
    return {
        "caller": {
            "user_id": user_id,
            "is_authenticated": True,
            "is_admin": is_admin,
        }
    }


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


def _conditional_check_failed_error() -> ClientError:
    return ClientError(
        error_response={"Error": {"Code": "ConditionalCheckFailedException", "Message": "conditional failed"}},
        operation_name="UpdateItem",
    )


@pytest.fixture
def mock_table(monkeypatch):
    # Replace the real DynamoDB resource with a mock so the tests validate
    # handler behavior without making any AWS calls.
    table = Mock()

    monkeypatch.setenv("EVENTS_TABLE_NAME", "example-events")
    monkeypatch.setattr(handler, "_get_dynamodb_table", lambda _table_name: table)

    return table


def test_lambda_handler_allows_creator_to_update_one_field(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(),
    }
    mock_table.update_item.return_value = {
        "Attributes": _valid_item(title="Updated Launch Event"),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "title": "Updated Launch Event",
        },
        None,
    )

    assert response["statusCode"] == 200
    assert response["headers"] == {"Content-Type": "application/json"}
    assert json.loads(response["body"]) == {
        "item": {
            "event_id": "11111111-1111-1111-1111-111111111111",
            "status": "ACTIVE",
            "title": "Updated Launch Event",
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
    assert "event_pk" not in json.loads(response["body"])["item"]

    mock_table.get_item.assert_called_once_with(
        Key={"event_pk": "EVENT#11111111-1111-1111-1111-111111111111"}
    )
    mock_table.update_item.assert_called_once()


def test_lambda_handler_allows_creator_to_update_multiple_fields(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(),
    }
    mock_table.update_item.return_value = {
        "Attributes": _valid_item(
            title="Updated Launch Event",
            location="Hamburg",
            capacity=Decimal("75"),
        ),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "title": "Updated Launch Event",
            "location": "Hamburg",
            "capacity": 75,
        },
        None,
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["item"]["status"] == "ACTIVE"
    assert json.loads(response["body"])["item"]["title"] == "Updated Launch Event"
    assert json.loads(response["body"])["item"]["location"] == "Hamburg"
    assert json.loads(response["body"])["item"]["capacity"] == 75


def test_lambda_handler_allows_admin_to_update_someone_elses_event(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(creator_id="bob"),
    }
    mock_table.update_item.return_value = {
        "Attributes": _valid_item(creator_id="bob", requires_admin=True),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice", is_admin=True),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "requires_admin": True,
        },
        None,
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["item"]["status"] == "ACTIVE"
    assert json.loads(response["body"])["item"]["requires_admin"] is True


def test_lambda_handler_accepts_api_gateway_body_json(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(),
    }
    mock_table.update_item.return_value = {
        "Attributes": _valid_item(description="Updated from API Gateway body"),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "pathParameters": {"event_id": "11111111-1111-1111-1111-111111111111"},
            "body": json.dumps({"description": "Updated from API Gateway body"}),
            "description": "top-level-should-be-ignored",
        },
        None,
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["item"]["status"] == "ACTIVE"
    assert json.loads(response["body"])["item"]["description"] == "Updated from API Gateway body"


def test_lambda_handler_prefers_path_parameters_over_top_level_event_id(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(event_pk="EVENT#22222222-2222-2222-2222-222222222222"),
    }
    mock_table.update_item.return_value = {
        "Attributes": _valid_item(
            event_pk="EVENT#22222222-2222-2222-2222-222222222222",
            title="Ownership Check",
        ),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "top-level-id-should-not-be-used",
            "pathParameters": {"event_id": "22222222-2222-2222-2222-222222222222"},
            "title": "Ownership Check",
        },
        None,
    )

    assert response["statusCode"] == 200
    mock_table.get_item.assert_called_once_with(
        Key={"event_pk": "EVENT#22222222-2222-2222-2222-222222222222"}
    )


def test_lambda_handler_recomputes_gsi_helpers_when_date_changes(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(),
    }
    mock_table.update_item.return_value = {
        "Attributes": _valid_item(
            date="2026-08-20T00:00:00Z",
            creator_events_gsi_sk="2026-08-20T00:00:00Z#11111111-1111-1111-1111-111111111111",
            public_upcoming_gsi_sk="2026-08-20T00:00:00Z#11111111-1111-1111-1111-111111111111",
        ),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "date": "2026-08-20",
        },
        None,
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["item"]["status"] == "ACTIVE"
    assert json.loads(response["body"])["item"]["date"] == "2026-08-20T00:00:00Z"

    update_kwargs = mock_table.update_item.call_args.kwargs
    assert update_kwargs["ExpressionAttributeValues"][":creator_events_gsi_sk"] == (
        "2026-08-20T00:00:00Z#11111111-1111-1111-1111-111111111111"
    )
    assert update_kwargs["ExpressionAttributeValues"][":public_upcoming_gsi_sk"] == (
        "2026-08-20T00:00:00Z#11111111-1111-1111-1111-111111111111"
    )


def test_lambda_handler_removes_public_gsi_helpers_when_event_becomes_private(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(is_public=True),
    }
    mock_table.update_item.return_value = {
        "Attributes": _valid_item(
            is_public=False,
            public_upcoming_gsi_pk=None,
            public_upcoming_gsi_sk=None,
        ),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "is_public": False,
        },
        None,
    )

    assert response["statusCode"] == 200
    update_expression = mock_table.update_item.call_args.kwargs["UpdateExpression"]
    assert "REMOVE #public_upcoming_gsi_pk, #public_upcoming_gsi_sk" in update_expression


def test_lambda_handler_adds_public_gsi_helpers_when_event_becomes_public(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(
            is_public=False,
            public_upcoming_gsi_pk=None,
            public_upcoming_gsi_sk=None,
        ),
    }
    mock_table.update_item.return_value = {
        "Attributes": _valid_item(
            is_public=True,
            public_upcoming_gsi_pk="PUBLIC",
            public_upcoming_gsi_sk="2026-06-15T00:00:00Z#11111111-1111-1111-1111-111111111111",
        ),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "is_public": True,
        },
        None,
    )

    assert response["statusCode"] == 200
    update_kwargs = mock_table.update_item.call_args.kwargs
    assert update_kwargs["ExpressionAttributeValues"][":public_upcoming_gsi_pk"] == "PUBLIC"


def test_lambda_handler_allows_capacity_to_be_set_to_null(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(capacity=Decimal("50")),
    }
    mock_table.update_item.return_value = {
        "Attributes": _valid_item(capacity=None),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "capacity": None,
        },
        None,
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["item"]["status"] == "ACTIVE"
    assert json.loads(response["body"])["item"]["capacity"] is None

    update_kwargs = mock_table.update_item.call_args.kwargs
    assert "#attending_count <= :capacity_limit" not in update_kwargs["ConditionExpression"]


def test_lambda_handler_returns_400_for_missing_event_id(mock_table):
    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "title": "Updated Launch Event",
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {"message": "event_id is required."}
    mock_table.get_item.assert_not_called()


def test_lambda_handler_returns_400_for_blank_event_id(mock_table):
    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "   ",
            "title": "Updated Launch Event",
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {"message": "event_id must be a non-empty string."}


def test_lambda_handler_returns_400_for_internal_storage_key_input(mock_table):
    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "EVENT#abc",
            "title": "Updated Launch Event",
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "event_id must use the public identifier, not the internal storage key."
    }


def test_lambda_handler_returns_400_for_malformed_json_body(mock_table):
    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "body": "{not-valid-json}",
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {"message": "Request body must contain valid JSON."}


def test_lambda_handler_returns_400_when_body_json_is_not_an_object(mock_table):
    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "body": json.dumps(["not", "an", "object"]),
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {"message": "Request body JSON must be an object."}


def test_lambda_handler_returns_400_when_no_mutable_fields_are_provided(mock_table):
    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {"message": "At least one mutable field must be provided."}


def test_lambda_handler_returns_400_for_unknown_field(mock_table):
    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "unknown_field": "value",
        },
        None,
    )

    assert response["statusCode"] == 400
    assert "Unknown update fields are not allowed" in json.loads(response["body"])["message"]


def test_lambda_handler_returns_400_for_immutable_field(mock_table):
    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "created_at": "2026-04-05T00:00:00Z",
        },
        None,
    )

    assert response["statusCode"] == 400
    assert "Immutable fields cannot be updated" in json.loads(response["body"])["message"]


def test_lambda_handler_returns_400_when_status_is_provided_in_payload(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "status": "CANCELLED",
        },
        None,
    )

    assert response["statusCode"] == 400
    assert "Immutable fields cannot be updated" in json.loads(response["body"])["message"]


def test_lambda_handler_returns_400_for_invalid_title(mock_table):
    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "title": "   ",
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {"message": "title must be a non-empty string when provided."}


def test_lambda_handler_returns_400_for_invalid_date(mock_table):
    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "date": "not-a-date",
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {"message": "date must use ISO 8601 format."}


def test_lambda_handler_returns_400_for_invalid_capacity(mock_table):
    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "capacity": 0,
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "capacity must be null or an integer greater than or equal to 1."
    }


def test_lambda_handler_returns_400_when_non_admin_sets_requires_admin_true(mock_table):
    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice", is_admin=False),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "requires_admin": True,
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "admin privileges are required to make an event admin-only."
    }


def test_lambda_handler_returns_400_when_capacity_is_below_current_attending_count(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(attending_count=Decimal("3")),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "capacity": 2,
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "capacity cannot be reduced below the current number of attending RSVPs."
    }


def test_lambda_handler_returns_400_for_cancelled_event(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(status="CANCELLED"),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "title": "Updated Launch Event",
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "Cancelled events cannot be updated."
    }


def test_lambda_handler_returns_403_for_authenticated_non_owner_non_admin(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(creator_id="bob"),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice", is_admin=False),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "title": "Unauthorized Update",
        },
        None,
    )

    assert response["statusCode"] == 403
    assert json.loads(response["body"]) == {"message": "You are not allowed to update this event."}


def test_lambda_handler_returns_404_when_event_does_not_exist(mock_table):
    mock_table.get_item.return_value = {}

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "title": "Updated Launch Event",
        },
        None,
    )

    assert response["statusCode"] == 404
    assert json.loads(response["body"]) == {"message": "Event not found."}


def test_lambda_handler_returns_400_when_capacity_race_is_detected_on_conditional_reread(mock_table):
    mock_table.get_item.side_effect = [
        {"Item": _valid_item(attending_count=Decimal("2"))},
        {"Item": _valid_item(attending_count=Decimal("4"))},
    ]
    mock_table.update_item.side_effect = _conditional_check_failed_error()

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "capacity": 3,
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "capacity cannot be reduced below the current number of attending RSVPs."
    }


def test_lambda_handler_returns_500_for_unexpected_conditional_update_failure(mock_table):
    mock_table.get_item.side_effect = [
        {"Item": _valid_item(attending_count=Decimal("2"))},
        {"Item": _valid_item(attending_count=Decimal("2"))},
    ]
    mock_table.update_item.side_effect = _conditional_check_failed_error()

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "capacity": 3,
        },
        None,
    )

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {"message": "Internal server error."}


def test_lambda_handler_returns_500_for_invalid_stored_event_key_shape(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(event_pk="bad-storage-key"),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "title": "Updated Launch Event",
        },
        None,
    )

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {"message": "Internal server error."}


def test_lambda_handler_returns_500_for_invalid_stored_creator_id_shape(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(creator_id=None),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "title": "Updated Launch Event",
        },
        None,
    )

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {"message": "Internal server error."}


def test_lambda_handler_returns_500_for_missing_stored_status(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(status=None),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "title": "Updated Launch Event",
        },
        None,
    )

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {"message": "Internal server error."}


def test_lambda_handler_returns_500_for_invalid_stored_attending_count_shape(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(attending_count="two"),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "title": "Updated Launch Event",
        },
        None,
    )

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {"message": "Internal server error."}


def test_lambda_handler_returns_500_for_invalid_updated_dynamodb_item_mapping(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(),
    }
    mock_table.update_item.return_value = {
        "Attributes": _valid_item(title=["not-a-string"]),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "title": "Updated Launch Event",
        },
        None,
    )

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {"message": "Internal server error."}


def test_lambda_handler_returns_500_for_invalid_updated_status_mapping(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(),
    }
    mock_table.update_item.return_value = {
        "Attributes": _valid_item(status="ARCHIVED"),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
            "title": "Updated Launch Event",
        },
        None,
    )

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {"message": "Internal server error."}
