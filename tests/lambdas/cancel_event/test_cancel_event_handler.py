import json
from decimal import Decimal
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from lambdas.cancel_event import handler


def _authenticated_event(*, user_id: str = "alice", is_admin: bool = False) -> dict[str, object]:
    # Use the normalized synthetic caller test shape supported by the shared
    # auth helper so these tests stay focused on cancel-event business rules
    # instead of one raw authorizer transport format.
    return {
        "caller": {
            "user_id": user_id,
            "is_authenticated": True,
            "is_admin": is_admin,
        }
    }


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
    }
    item.update(overrides)

    event_id = str(item["event_pk"]).removeprefix("EVENT#")
    item["creator_events_gsi_pk"] = f"CREATOR#{item['creator_id']}"
    item["creator_events_gsi_sk"] = f"{item['date']}#{event_id}"

    if item["is_public"]:
        item["public_upcoming_gsi_pk"] = "PUBLIC"
        item["public_upcoming_gsi_sk"] = f"{item['date']}#{event_id}"
    else:
        item.pop("public_upcoming_gsi_pk", None)
        item.pop("public_upcoming_gsi_sk", None)

    return item


def _cancelled_item(**overrides) -> dict[str, object]:
    item = _valid_item(status="CANCELLED", **overrides)
    item.pop("public_upcoming_gsi_pk", None)
    item.pop("public_upcoming_gsi_sk", None)
    return item


def _conditional_check_failed_error() -> ClientError:
    return ClientError(
        error_response={"Error": {"Code": "ConditionalCheckFailedException", "Message": "conditional failed"}},
        operation_name="UpdateItem",
    )


@pytest.fixture
def mock_table(monkeypatch):
    table = Mock()

    monkeypatch.setenv("EVENTS_TABLE_NAME", "example-events")
    monkeypatch.setattr(handler, "_get_dynamodb_table", lambda _table_name: table)

    return table


def test_lambda_handler_allows_creator_to_cancel_active_event(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(),
    }
    mock_table.update_item.return_value = {
        "Attributes": _cancelled_item(),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
        },
        None,
    )

    assert response["statusCode"] == 200
    assert response["headers"] == {"Content-Type": "application/json"}
    body = json.loads(response["body"])
    assert body == {
        "item": {
            "event_id": "11111111-1111-1111-1111-111111111111",
            "status": "CANCELLED",
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
    mock_table.update_item.assert_called_once()
    update_kwargs = mock_table.update_item.call_args.kwargs
    assert update_kwargs["ConditionExpression"] == "attribute_exists(event_pk) AND #status = :active"
    assert update_kwargs["UpdateExpression"] == (
        "SET #status = :cancelled REMOVE public_upcoming_gsi_pk, public_upcoming_gsi_sk"
    )
    assert update_kwargs["ExpressionAttributeValues"] == {
        ":active": "ACTIVE",
        ":cancelled": "CANCELLED",
    }
    assert update_kwargs["ExpressionAttributeNames"] == {
    "#status": "status",
    }


def test_lambda_handler_allows_admin_to_cancel_someone_elses_event(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(creator_id="bob"),
    }
    mock_table.update_item.return_value = {
        "Attributes": _cancelled_item(creator_id="bob"),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="admin-user", is_admin=True),
            "event_id": "11111111-1111-1111-1111-111111111111",
        },
        None,
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["item"]["status"] == "CANCELLED"
    assert json.loads(response["body"])["item"]["created_by"] == "bob"


def test_lambda_handler_returns_success_idempotently_for_already_cancelled_event(mock_table):
    mock_table.get_item.return_value = {
        "Item": _cancelled_item(),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
        },
        None,
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["item"]["status"] == "CANCELLED"
    mock_table.update_item.assert_not_called()


def test_lambda_handler_returns_403_for_authenticated_non_owner_non_admin(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(creator_id="bob"),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="mallory"),
            "event_id": "11111111-1111-1111-1111-111111111111",
        },
        None,
    )

    assert response["statusCode"] == 403
    assert json.loads(response["body"]) == {"message": "You are not allowed to cancel this event."}
    mock_table.update_item.assert_not_called()


def test_lambda_handler_returns_404_when_event_does_not_exist(mock_table):
    mock_table.get_item.return_value = {}

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
        },
        None,
    )

    assert response["statusCode"] == 404
    assert json.loads(response["body"]) == {"message": "Event not found."}
    mock_table.update_item.assert_not_called()


def test_lambda_handler_accepts_path_parameters_for_event_id(mock_table):
    mock_table.get_item.return_value = {
        "Item": _valid_item(event_pk="EVENT#22222222-2222-2222-2222-222222222222"),
    }
    mock_table.update_item.return_value = {
        "Attributes": _cancelled_item(event_pk="EVENT#22222222-2222-2222-2222-222222222222"),
    }

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "top-level-should-not-be-used",
            "pathParameters": {"event_id": "22222222-2222-2222-2222-222222222222"},
        },
        None,
    )

    assert response["statusCode"] == 200
    mock_table.get_item.assert_called_once_with(
        Key={"event_pk": "EVENT#22222222-2222-2222-2222-222222222222"}
    )


def test_lambda_handler_returns_400_for_missing_event_id(mock_table):
    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {"message": "event_id is required."}
    mock_table.get_item.assert_not_called()


def test_lambda_handler_returns_400_for_internal_storage_key_input(mock_table):
    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "EVENT#abc",
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {
        "message": "event_id must use the public identifier, not the internal storage key."
    }


def test_lambda_handler_returns_400_for_missing_caller_context(mock_table):
    response = handler.lambda_handler(
        {
            "event_id": "11111111-1111-1111-1111-111111111111",
        },
        None,
    )

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {"message": "Authenticated caller context is required."}
    mock_table.get_item.assert_not_called()


def test_lambda_handler_returns_200_when_conditional_reread_shows_event_is_now_cancelled(mock_table):
    mock_table.get_item.side_effect = [
        {"Item": _valid_item()},
        {"Item": _cancelled_item()},
    ]
    mock_table.update_item.side_effect = _conditional_check_failed_error()

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
        },
        None,
    )

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["item"]["status"] == "CANCELLED"


def test_lambda_handler_returns_500_for_unexpected_conditional_cancel_failure(mock_table):
    mock_table.get_item.side_effect = [
        {"Item": _valid_item()},
        {"Item": _valid_item()},
    ]
    mock_table.update_item.side_effect = _conditional_check_failed_error()

    response = handler.lambda_handler(
        {
            **_authenticated_event(user_id="alice"),
            "event_id": "11111111-1111-1111-1111-111111111111",
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
        },
        None,
    )

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {"message": "Internal server error."}
