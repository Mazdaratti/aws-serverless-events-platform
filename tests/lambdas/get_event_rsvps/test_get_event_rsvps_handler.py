import base64
import json

import pytest

from lambdas.get_event_rsvps import handler


UNSET = object()
EVENT_ID = "11111111-1111-1111-1111-111111111111"
OTHER_EVENT_ID = "22222222-2222-2222-2222-222222222222"


def build_authorizer(
    *,
    user_id: object = "alice",
    is_authenticated: object = True,
    is_admin: object = False,
) -> dict[str, object]:
    """Build the normalized flat caller shape used by shared auth parsing."""
    return {
        "is_authenticated": is_authenticated,
        "user_id": user_id,
        "is_admin": is_admin,
    }


def build_direct_event(
    *,
    event_id: object = EVENT_ID,
    limit: object = UNSET,
    next_cursor: object = UNSET,
    authorizer: object = UNSET,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build a direct-invocation event so tests can vary one input at a time."""
    event: dict[str, object] = {}

    if event_id is not UNSET:
        event["event_id"] = event_id
    if limit is not UNSET:
        event["limit"] = limit
    if next_cursor is not UNSET:
        event["next_cursor"] = next_cursor
    if authorizer is not UNSET:
        event["requestContext"] = {"authorizer": authorizer}
    if extra:
        event.update(extra)

    return event


def build_api_gateway_event(
    *,
    event_id: object = EVENT_ID,
    query_limit: object = UNSET,
    query_next_cursor: object = UNSET,
    top_level_event_id: object = UNSET,
    top_level_limit: object = UNSET,
    top_level_next_cursor: object = UNSET,
    authorizer: object = UNSET,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build an API Gateway-style event with path/query parameter support."""
    query_params: dict[str, object] = {}
    if query_limit is not UNSET:
        query_params["limit"] = query_limit
    if query_next_cursor is not UNSET:
        query_params["next_cursor"] = query_next_cursor

    event: dict[str, object] = {}
    if event_id is not UNSET:
        event["pathParameters"] = {"event_id": event_id}
    if query_params:
        event["queryStringParameters"] = query_params
    if top_level_event_id is not UNSET:
        event["event_id"] = top_level_event_id
    if top_level_limit is not UNSET:
        event["limit"] = top_level_limit
    if top_level_next_cursor is not UNSET:
        event["next_cursor"] = top_level_next_cursor
    if authorizer is not UNSET:
        event["requestContext"] = {"authorizer": authorizer}
    if extra:
        event.update(extra)

    return event


def build_event_item(
    *,
    event_id: str = EVENT_ID,
    status: str = "ACTIVE",
    title: str = "Platform Launch Event",
    date: str = "2026-06-15T00:00:00Z",
    capacity: int | None = 50,
    creator_id: str = "alice",
    rsvp_total: int = 3,
    attending_count: int = 2,
    not_attending_count: int = 1,
) -> dict[str, object]:
    """Build the low-level DynamoDB event item shape consumed by the handler."""
    item: dict[str, object] = {
        "event_pk": {"S": f"EVENT#{event_id}"},
        "status": {"S": status},
        "title": {"S": title},
        "date": {"S": date},
        "creator_id": {"S": creator_id},
        "rsvp_total": {"N": str(rsvp_total)},
        "attending_count": {"N": str(attending_count)},
        "not_attending_count": {"N": str(not_attending_count)},
    }

    if capacity is None:
        item["capacity"] = {"NULL": True}
    else:
        item["capacity"] = {"N": str(capacity)}

    return item


def build_rsvp_item(
    *,
    event_id: str = EVENT_ID,
    subject_sk: str = "USER#alice",
    subject_type: str = "USER",
    user_id: str | None = "alice",
    attending: bool = True,
    created_at: str = "2026-04-01T10:00:00Z",
    updated_at: str = "2026-04-01T10:00:00Z",
    anonymous_token: str | None = None,
) -> dict[str, object]:
    """Build the low-level DynamoDB RSVP item shape returned by the query path."""
    item: dict[str, object] = {
        "event_pk": {"S": f"EVENT#{event_id}"},
        "subject_sk": {"S": subject_sk},
        "subject_type": {"S": subject_type},
        "attending": {"BOOL": attending},
        "created_at": {"S": created_at},
        "updated_at": {"S": updated_at},
    }

    if user_id is not None:
        item["user_id"] = {"S": user_id}
    if anonymous_token is not None:
        item["anonymous_token"] = {"S": anonymous_token}

    return item


def build_event_key(event_id: str = EVENT_ID) -> dict[str, object]:
    """Build the low-level DynamoDB key used for event GetItem reads."""
    return {"event_pk": {"S": f"EVENT#{event_id}"}}


def build_cursor(*, event_id: str = EVENT_ID, subject_sk: str = "USER#alice") -> str:
    """Build one opaque pagination cursor using the public cursor contract."""
    payload = {
        "event_pk": {"S": f"EVENT#{event_id}"},
        "subject_sk": {"S": subject_sk},
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("utf-8")
    return encoded.rstrip("=")


def decode_body(response: dict[str, object]) -> dict[str, object]:
    """Decode the Lambda JSON body so tests can assert the business response shape directly."""
    return json.loads(response["body"])


def assert_success_status(response: dict[str, object], expected_status: int) -> dict[str, object]:
    """Assert the standard wrapped success response and return the decoded body."""
    assert response["statusCode"] == expected_status
    assert response["headers"] == {"Content-Type": "application/json"}
    return decode_body(response)


def assert_error_response(response: dict[str, object], *, status_code: int, message: str) -> None:
    """Assert the standard wrapped error response for validation and business failures."""
    assert response["statusCode"] == status_code
    assert response["headers"] == {"Content-Type": "application/json"}
    assert decode_body(response) == {"message": message}


class FakeDynamoDBClient:
    """Tiny fake low-level DynamoDB client for focused get-event-rsvps tests."""

    def __init__(self) -> None:
        self.get_sequences: dict[tuple[str, str], list[dict[str, object]]] = {}
        self.get_calls: list[dict[str, object]] = []
        self.query_calls: list[dict[str, object]] = []
        self.query_responses: list[dict[str, object]] = []

    def queue_get_item(self, table_name: str, key: dict[str, object], *responses: dict[str, object]) -> None:
        self.get_sequences[(table_name, self._serialize_obj(key))] = [dict(response) for response in responses]

    def queue_query(self, *responses: dict[str, object]) -> None:
        self.query_responses.extend(dict(response) for response in responses)

    def get_item(self, *, TableName: str, Key: dict[str, object]) -> dict[str, object]:
        self.get_calls.append({"TableName": TableName, "Key": Key})
        queue = self.get_sequences.get((TableName, self._serialize_obj(Key)))
        if not queue:
            return {}
        if len(queue) == 1:
            return dict(queue[0])
        return dict(queue.pop(0))

    def query(self, **kwargs: object) -> dict[str, object]:
        self.query_calls.append(dict(kwargs))
        if not self.query_responses:
            return {}
        return dict(self.query_responses.pop(0))

    @staticmethod
    def _serialize_obj(value: object) -> str:
        return json.dumps(value, sort_keys=True)


@pytest.fixture
def fake_client(monkeypatch) -> FakeDynamoDBClient:
    """Wire the handler to a fake DynamoDB client and stable test table names."""
    client = FakeDynamoDBClient()
    monkeypatch.setenv("EVENTS_TABLE_NAME", "example-events")
    monkeypatch.setenv("RSVPS_TABLE_NAME", "example-rsvps")
    monkeypatch.setattr(handler, "_get_dynamodb_client", lambda: client)
    return client


# request validation


def test_lambda_handler_returns_400_for_missing_event_id(fake_client):
    response = handler.lambda_handler(build_direct_event(event_id=UNSET), None)

    assert_error_response(response, status_code=400, message="event_id is required.")
    assert fake_client.get_calls == []
    assert fake_client.query_calls == []


def test_lambda_handler_returns_400_for_blank_event_id(fake_client):
    response = handler.lambda_handler(build_direct_event(event_id="   "), None)

    assert_error_response(response, status_code=400, message="event_id must be a non-empty string.")


def test_lambda_handler_returns_400_for_internal_storage_event_id(fake_client):
    response = handler.lambda_handler(build_direct_event(event_id="EVENT#abc"), None)

    assert_error_response(
        response,
        status_code=400,
        message="event_id must use the public identifier, not the internal storage key.",
    )


def test_lambda_handler_returns_400_for_invalid_path_parameters_shape(fake_client):
    response = handler.lambda_handler(
        build_direct_event(extra={"pathParameters": "not-an-object"}),
        None,
    )

    assert_error_response(response, status_code=400, message="pathParameters must be an object when provided.")


def test_lambda_handler_returns_400_for_invalid_query_string_parameters_shape(fake_client):
    response = handler.lambda_handler(
        build_direct_event(extra={"queryStringParameters": "not-an-object"}),
        None,
    )

    assert_error_response(
        response,
        status_code=400,
        message="queryStringParameters must be an object when provided.",
    )


def test_lambda_handler_returns_400_for_invalid_limit(fake_client):
    response = handler.lambda_handler(build_direct_event(limit="abc"), None)

    assert_error_response(response, status_code=400, message="limit must be an integer between 1 and 100.")


def test_lambda_handler_returns_400_for_limit_above_max(fake_client):
    response = handler.lambda_handler(build_direct_event(limit=101), None)

    assert_error_response(response, status_code=400, message="limit must be an integer between 1 and 100.")


def test_lambda_handler_returns_400_for_invalid_cursor(fake_client):
    response = handler.lambda_handler(build_direct_event(next_cursor="%%%not-a-valid-cursor%%%"), None)

    assert_error_response(response, status_code=400, message="next_cursor must be a valid opaque cursor.")


def test_lambda_handler_returns_400_for_cursor_from_different_event(fake_client):
    response = handler.lambda_handler(
        build_direct_event(event_id=EVENT_ID, next_cursor=build_cursor(event_id=OTHER_EVENT_ID)),
        None,
    )

    assert_error_response(response, status_code=400, message="next_cursor must belong to the requested event.")


def test_lambda_handler_returns_400_for_invalid_request_context_shape(fake_client):
    response = handler.lambda_handler(
        build_direct_event(extra={"requestContext": "not-an-object"}),
        None,
    )

    assert_error_response(response, status_code=400, message="requestContext must be an object when provided.")


def test_lambda_handler_returns_400_for_invalid_authorizer_shape(fake_client):
    response = handler.lambda_handler(
        build_direct_event(extra={"requestContext": {"authorizer": "not-an-object"}}),
        None,
    )

    assert_error_response(
        response,
        status_code=400,
        message="requestContext.authorizer must be an object when provided.",
    )


def test_lambda_handler_returns_400_for_invalid_authorizer_user_id_type(fake_client):
    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id=123)),
        None,
    )

    assert_error_response(
        response,
        status_code=400,
        message="requestContext.authorizer.user_id must be a string when provided.",
    )


def test_lambda_handler_returns_400_for_invalid_authorizer_is_admin_type(fake_client):
    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(is_admin={"bad": True})),
        None,
    )

    assert_error_response(
        response,
        status_code=400,
        message="requestContext.authorizer.is_admin must be a boolean-like value when provided.",
    )


# request resolution


def test_lambda_handler_prefers_path_parameters_over_top_level_event_id(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(OTHER_EVENT_ID),
        {"Item": build_event_item(event_id=OTHER_EVENT_ID)},
    )
    fake_client.queue_query({"Items": []})

    response = handler.lambda_handler(
        build_api_gateway_event(
            event_id=OTHER_EVENT_ID,
            top_level_event_id="should-not-be-used",
            authorizer=build_authorizer(user_id="alice"),
        ),
        None,
    )

    assert response["statusCode"] == 200
    assert fake_client.get_calls[0]["Key"] == build_event_key(OTHER_EVENT_ID)


def test_lambda_handler_returns_400_when_path_parameter_event_id_is_none_even_if_top_level_exists(fake_client):
    response = handler.lambda_handler(
        build_direct_event(
            event_id="top-level-should-not-be-used",
            extra={"pathParameters": {"event_id": None}},
        ),
        None,
    )

    assert_error_response(response, status_code=400, message="event_id is required.")
    assert fake_client.get_calls == []
    assert fake_client.query_calls == []


def test_lambda_handler_prefers_query_string_limit_over_top_level_limit(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item()})
    fake_client.queue_query({"Items": []})

    response = handler.lambda_handler(
        build_api_gateway_event(
            query_limit="5",
            top_level_limit=99,
            authorizer=build_authorizer(user_id="alice"),
        ),
        None,
    )

    assert response["statusCode"] == 200
    assert fake_client.query_calls[0]["Limit"] == 5


def test_lambda_handler_uses_default_limit_when_not_provided(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item()})
    fake_client.queue_query({"Items": []})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice")),
        None,
    )

    assert response["statusCode"] == 200
    assert fake_client.query_calls[0]["Limit"] == 50


def test_lambda_handler_prefers_query_string_next_cursor_over_top_level_next_cursor(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item()})
    fake_client.queue_query({"Items": []})

    response = handler.lambda_handler(
        build_api_gateway_event(
            query_next_cursor=build_cursor(subject_sk="USER#query"),
            top_level_next_cursor=build_cursor(subject_sk="USER#top-level"),
            authorizer=build_authorizer(user_id="alice"),
        ),
        None,
    )

    assert response["statusCode"] == 200
    assert fake_client.query_calls[0]["ExclusiveStartKey"] == {
        "event_pk": {"S": f"EVENT#{EVENT_ID}"},
        "subject_sk": {"S": "USER#query"},
    }


def test_lambda_handler_treats_blank_next_cursor_as_no_cursor(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item()})
    fake_client.queue_query({"Items": []})

    response = handler.lambda_handler(
        build_api_gateway_event(
            query_next_cursor="   ",
            authorizer=build_authorizer(user_id="alice"),
        ),
        None,
    )

    assert response["statusCode"] == 200
    assert "ExclusiveStartKey" not in fake_client.query_calls[0]


# existence and authorization


def test_lambda_handler_returns_404_when_event_does_not_exist(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice")),
        None,
    )

    assert_error_response(response, status_code=404, message="Event not found.")
    assert fake_client.query_calls == []


def test_lambda_handler_returns_404_for_missing_event_before_authorization_check(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {})

    response = handler.lambda_handler(build_direct_event(), None)

    assert_error_response(response, status_code=404, message="Event not found.")
    assert fake_client.query_calls == []


def test_lambda_handler_returns_403_for_anonymous_caller_on_existing_event(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item()})

    response = handler.lambda_handler(build_direct_event(), None)

    assert_error_response(
        response,
        status_code=403,
        message="You do not have permission to view RSVPs for this event.",
    )
    assert fake_client.query_calls == []


def test_lambda_handler_returns_403_for_authenticated_non_owner_non_admin(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item(creator_id="alice")})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="bob", is_admin=False)),
        None,
    )

    assert_error_response(
        response,
        status_code=403,
        message="You do not have permission to view RSVPs for this event.",
    )
    assert fake_client.query_calls == []


def test_lambda_handler_treats_blank_authorizer_user_id_as_anonymous(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item(creator_id="alice")})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="   ", is_admin=False)),
        None,
    )

    assert_error_response(
        response,
        status_code=403,
        message="You do not have permission to view RSVPs for this event.",
    )
    assert fake_client.query_calls == []


def test_lambda_handler_allows_creator_to_read_active_event_rsvps(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item(status="ACTIVE", creator_id="alice")})
    fake_client.queue_query({"Items": []})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice", is_admin=False)),
        None,
    )

    assert response["statusCode"] == 200


def test_lambda_handler_allows_admin_to_read_cancelled_event_rsvps(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(status="CANCELLED", creator_id="alice")},
    )
    fake_client.queue_query({"Items": []})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="admin-user", is_admin=True)),
        None,
    )

    assert response["statusCode"] == 200


# success contract


def test_lambda_handler_returns_compact_event_summary_items_stats_and_no_internal_fields(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {
            "Item": build_event_item(
                event_id=EVENT_ID,
                status="ACTIVE",
                title="Python Meetup",
                date="2026-05-20T18:00:00Z",
                capacity=50,
                creator_id="alice",
                rsvp_total=3,
                attending_count=2,
                not_attending_count=1,
            )
        },
    )
    fake_client.queue_query(
        {
            "Items": [
                build_rsvp_item(
                    subject_sk="USER#alice",
                    subject_type="USER",
                    user_id="alice",
                    attending=True,
                    created_at="2026-04-08T10:00:00Z",
                    updated_at="2026-04-08T10:00:00Z",
                ),
                build_rsvp_item(
                    subject_sk="ANON#browser-123",
                    subject_type="ANON",
                    user_id=None,
                    attending=False,
                    created_at="2026-04-08T10:05:00Z",
                    updated_at="2026-04-08T10:05:00Z",
                    anonymous_token="browser-123",
                ),
            ]
        }
    )

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice")),
        None,
    )

    body = assert_success_status(response, 200)
    assert body == {
        "event": {
            "event_id": EVENT_ID,
            "status": "ACTIVE",
            "title": "Python Meetup",
            "date": "2026-05-20T18:00:00Z",
            "capacity": 50,
            "created_by": "alice",
            "rsvp_count": 3,
            "attending_count": 2,
        },
        "items": [
            {
                "subject": {
                    "type": "USER",
                    "user_id": "alice",
                    "anonymous": False,
                },
                "attending": True,
                "created_at": "2026-04-08T10:00:00Z",
                "updated_at": "2026-04-08T10:00:00Z",
            },
            {
                "subject": {
                    "type": "ANON",
                    "user_id": None,
                    "anonymous": True,
                },
                "attending": False,
                "created_at": "2026-04-08T10:05:00Z",
                "updated_at": "2026-04-08T10:05:00Z",
            },
        ],
        "stats": {
            "total": 3,
            "attending": 2,
            "not_attending": 1,
        },
        "next_cursor": None,
    }
    assert "subject_sk" not in body["items"][0]
    assert "anonymous_token" not in body["items"][1]
    assert "event_pk" not in body["items"][0]


def test_lambda_handler_returns_200_with_empty_items_and_zero_stats_for_existing_event(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(rsvp_total=0, attending_count=0, not_attending_count=0)},
    )
    fake_client.queue_query({"Items": []})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice")),
        None,
    )

    body = assert_success_status(response, 200)
    assert body["items"] == []
    assert body["stats"] == {
        "total": 0,
        "attending": 0,
        "not_attending": 0,
    }
    assert body["next_cursor"] is None


# pagination


def test_lambda_handler_uses_and_returns_opaque_cursor_for_pagination(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item()})
    fake_client.queue_query(
        {
            "Items": [],
            "LastEvaluatedKey": {
                "event_pk": {"S": f"EVENT#{EVENT_ID}"},
                "subject_sk": {"S": "USER#charlie"},
            },
        }
    )

    incoming_cursor = build_cursor(event_id=EVENT_ID, subject_sk="USER#alice")

    response = handler.lambda_handler(
        build_direct_event(
            authorizer=build_authorizer(user_id="alice"),
            next_cursor=incoming_cursor,
        ),
        None,
    )

    body = assert_success_status(response, 200)
    assert fake_client.query_calls[0]["ExclusiveStartKey"] == {
        "event_pk": {"S": f"EVENT#{EVENT_ID}"},
        "subject_sk": {"S": "USER#alice"},
    }
    assert body["next_cursor"] == build_cursor(event_id=EVENT_ID, subject_sk="USER#charlie")


# deserialization and runtime shape checks


def test_lambda_handler_returns_500_for_invalid_event_status(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(status="DRAFT")},
    )

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice")),
        None,
    )

    assert_error_response(response, status_code=500, message="Internal server error.")


def test_lambda_handler_returns_500_for_invalid_rsvp_subject_type(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item()})
    fake_client.queue_query(
        {
            "Items": [
                build_rsvp_item(
                    subject_sk="MYSTERY#x",
                    subject_type="MYSTERY",
                    user_id=None,
                )
            ]
        }
    )

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice")),
        None,
    )

    assert_error_response(response, status_code=500, message="Internal server error.")


def test_lambda_handler_returns_500_for_invalid_user_rsvp_missing_user_id(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item()})
    fake_client.queue_query(
        {
            "Items": [
                build_rsvp_item(
                    subject_sk="USER#alice",
                    subject_type="USER",
                    user_id=None,
                )
            ]
        }
    )

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice")),
        None,
    )

    assert_error_response(response, status_code=500, message="Internal server error.")
