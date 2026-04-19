import json
from datetime import datetime, timezone

import pytest
from botocore.exceptions import ClientError

from lambdas.rsvp import handler


UNSET = object()
FIXED_NOW = datetime(2026, 4, 8, 12, 0, 0, tzinfo=timezone.utc)
FIXED_NOW_ISO = "2026-04-08T12:00:00Z"
FUTURE_DATE = "2026-06-15T00:00:00Z"
EVENT_DATE_EQUALS_NOW = "2026-04-08T12:00:00Z"
EVENT_ID = "11111111-1111-1111-1111-111111111111"


def build_authorizer(
    *,
    user_id: object = "alice",
    is_authenticated: object = True,
    is_admin: object = False,
) -> dict[str, object]:
    """Build the flat custom-authorizer shape supported by shared auth normalization."""
    return {
        "user_id": user_id,
        "is_authenticated": is_authenticated,
        "is_admin": is_admin,
    }


def build_lambda_authorizer(
    *,
    user_id: object = "alice",
    is_authenticated: bool | None = None,
    is_admin: object = False,
) -> dict[str, object]:
    """Build the real routed HTTP API simple-response Lambda authorizer shape."""
    if is_authenticated is None:
        is_authenticated = user_id is not None and (
            not isinstance(user_id, str) or bool(user_id.strip())
        )

    return {
        "lambda": {
            "user_id": user_id,
            "is_authenticated": is_authenticated,
            "is_admin": is_admin,
        }
    }


def build_direct_event(
    *,
    event_id: object = EVENT_ID,
    attending: object = True,
    anonymous_token: object = UNSET,
    authorizer: object = UNSET,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build a direct-invocation event so tests can focus on one input difference at a time."""
    event: dict[str, object] = {}

    if event_id is not UNSET:
        event["event_id"] = event_id
    if attending is not UNSET:
        event["attending"] = attending
    if anonymous_token is not UNSET:
        event["anonymous_token"] = anonymous_token
    if authorizer is not UNSET:
        event["requestContext"] = {"authorizer": authorizer}
    if extra:
        event.update(extra)

    return event


def build_api_gateway_event(
    *,
    event_id: object = EVENT_ID,
    body: object = UNSET,
    attending: object = True,
    anonymous_token: object = UNSET,
    authorizer: object = UNSET,
    top_level_event_id: object = UNSET,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build an API Gateway-style event with JSON body payload and optional path parameters."""
    payload: dict[str, object] = {}
    if attending is not UNSET:
        payload["attending"] = attending
    if anonymous_token is not UNSET:
        payload["anonymous_token"] = anonymous_token

    event: dict[str, object] = {}
    if event_id is not UNSET:
        event["pathParameters"] = {"event_id": event_id}
    if body is UNSET:
        event["body"] = json.dumps(payload)
    else:
        event["body"] = body
    if top_level_event_id is not UNSET:
        event["event_id"] = top_level_event_id
    if authorizer is not UNSET:
        event["requestContext"] = {"authorizer": authorizer}
    if extra:
        event.update(extra)

    return event


def build_event_item(
    *,
    event_id: str = EVENT_ID,
    status: str = "ACTIVE",
    date: str = FUTURE_DATE,
    is_public: bool = True,
    requires_admin: bool = False,
    capacity: int | None = 10,
    rsvp_total: int = 3,
    attending_count: int = 2,
    not_attending_count: int = 1,
) -> dict[str, object]:
    """Build the low-level DynamoDB event item shape consumed by the RSVP handler."""
    item: dict[str, object] = {
        "event_pk": {"S": f"EVENT#{event_id}"},
        "status": {"S": status},
        "date": {"S": date},
        "is_public": {"BOOL": is_public},
        "requires_admin": {"BOOL": requires_admin},
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
    attending: bool = True,
    created_at: str = "2026-04-01T10:00:00Z",
    updated_at: str = "2026-04-01T10:00:00Z",
    subject_type: str = "USER",
    user_id: str | None = "alice",
    anonymous_token: str | None = None,
) -> dict[str, object]:
    """Build the low-level DynamoDB RSVP item shape used for overwrite-state tests."""
    item: dict[str, object] = {
        "event_pk": {"S": f"EVENT#{event_id}"},
        "subject_sk": {"S": subject_sk},
        "attending": {"BOOL": attending},
        "created_at": {"S": created_at},
        "updated_at": {"S": updated_at},
        "subject_type": {"S": subject_type},
    }

    if user_id is not None:
        item["user_id"] = {"S": user_id}
    if anonymous_token is not None:
        item["anonymous_token"] = {"S": anonymous_token}

    return item


def build_event_key(event_id: str = EVENT_ID) -> dict[str, object]:
    """Build the low-level DynamoDB primary key for an event item."""
    return {"event_pk": {"S": f"EVENT#{event_id}"}}


def build_rsvp_key(*, event_id: str = EVENT_ID, subject_sk: str = "USER#alice") -> dict[str, object]:
    """Build the low-level DynamoDB primary key for one canonical RSVP subject record."""
    return {
        "event_pk": {"S": f"EVENT#{event_id}"},
        "subject_sk": {"S": subject_sk},
    }


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
    assert decode_body(response) == {"message": message}


def transaction_cancelled_error() -> ClientError:
    """Create the DynamoDB transaction-cancelled error that drives reclassification tests."""
    return ClientError(
        error_response={
            "Error": {
                "Code": "TransactionCanceledException",
                "Message": "transaction cancelled",
            }
        },
        operation_name="TransactWriteItems",
    )


class FakeDynamoDBClient:
    """Tiny fake low-level DynamoDB client for focused handler unit tests.

    The handler uses low-level client APIs for both `get_item` and
    `transact_write_items`, so the fake mirrors only those two calls. Tests can
    preload per-key responses, inspect the final transaction payload, and force
    one transaction failure path without pulling in heavier mocking machinery.
    """

    def __init__(self) -> None:
        self.get_sequences: dict[tuple[str, str], list[dict[str, object]]] = {}
        self.get_calls: list[dict[str, object]] = []
        self.transact_calls: list[dict[str, object]] = []
        self.transaction_error: ClientError | None = None

    def queue_get_item(self, table_name: str, key: dict[str, object], *responses: dict[str, object]) -> None:
        self.get_sequences[(table_name, self._serialize_key(key))] = [dict(response) for response in responses]

    def get_item(self, *, TableName: str, Key: dict[str, object]) -> dict[str, object]:
        self.get_calls.append({"TableName": TableName, "Key": Key})
        queue = self.get_sequences.get((TableName, self._serialize_key(Key)))
        if not queue:
            return {}
        if len(queue) == 1:
            return dict(queue[0])
        return dict(queue.pop(0))

    def transact_write_items(self, *, TransactItems: list[dict[str, object]]) -> None:
        self.transact_calls.append({"TransactItems": TransactItems})
        if self.transaction_error is not None:
            raise self.transaction_error

    @staticmethod
    def _serialize_key(key: dict[str, object]) -> str:
        return json.dumps(key, sort_keys=True)


@pytest.fixture(autouse=True)
def fixed_datetime(monkeypatch):
    """Freeze handler time so created/updated timestamps stay deterministic in tests."""
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return FIXED_NOW.replace(tzinfo=None)
            return FIXED_NOW.astimezone(tz)

    monkeypatch.setattr(handler, "datetime", FixedDateTime)


@pytest.fixture
def fake_client(monkeypatch) -> FakeDynamoDBClient:
    """Wire the RSVP handler to a fake DynamoDB client and stable test table names."""
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


def test_lambda_handler_returns_400_for_missing_attending(fake_client):
    response = handler.lambda_handler(build_direct_event(attending=UNSET), None)

    assert_error_response(response, status_code=400, message="attending is required.")


def test_lambda_handler_returns_400_for_non_boolean_attending(fake_client):
    response = handler.lambda_handler(build_direct_event(attending="yes"), None)

    assert_error_response(response, status_code=400, message="attending must be a boolean.")


def test_lambda_handler_returns_400_for_invalid_json_body(fake_client):
    response = handler.lambda_handler(
        build_api_gateway_event(body="{not-json", authorizer=build_authorizer()),
        None,
    )

    assert_error_response(response, status_code=400, message="Request body must contain valid JSON.")


def test_lambda_handler_returns_400_for_body_json_that_is_not_an_object(fake_client):
    response = handler.lambda_handler(
        build_api_gateway_event(body=json.dumps(["not", "an", "object"]), authorizer=build_authorizer()),
        None,
    )

    assert_error_response(response, status_code=400, message="Request body JSON must be an object.")


def test_lambda_handler_returns_400_for_missing_anonymous_token(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item(is_public=True)})

    response = handler.lambda_handler(build_direct_event(authorizer=UNSET, anonymous_token=UNSET), None)

    assert_error_response(response, status_code=400, message="anonymous_token is required for anonymous RSVP.")


def test_lambda_handler_returns_400_for_blank_anonymous_token_after_trim(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item(is_public=True)})

    response = handler.lambda_handler(build_direct_event(authorizer=UNSET, anonymous_token="   "), None)

    assert_error_response(response, status_code=400, message="anonymous_token is required for anonymous RSVP.")


def test_lambda_handler_returns_400_for_authenticated_caller_sending_anonymous_token(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item(is_public=True)})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice"), anonymous_token="anon-token"),
        None,
    )

    assert_error_response(
        response,
        status_code=400,
        message="anonymous_token must not be provided for authenticated RSVP.",
    )


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


def test_lambda_handler_returns_400_for_invalid_flat_authorizer_user_id_type(fake_client):
    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id=123)),
        None,
    )

    assert_error_response(
        response,
        status_code=400,
        message="requestContext.authorizer.user_id must be a string when provided.",
    )


def test_lambda_handler_returns_400_for_invalid_flat_authorizer_is_admin_type(fake_client):
    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice", is_admin={"bad": True})),
        None,
    )

    assert_error_response(
        response,
        status_code=400,
        message="requestContext.authorizer.is_admin must be a boolean when provided.",
    )


def test_lambda_handler_returns_400_for_invalid_lambda_authorizer_shape(fake_client):
    response = handler.lambda_handler(
        build_direct_event(authorizer={"lambda": "not-an-object"}),
        None,
    )

    assert_error_response(
        response,
        status_code=400,
        message="requestContext.authorizer.lambda must be an object when provided.",
    )


def test_lambda_handler_returns_400_for_invalid_lambda_authorizer_is_admin_type(fake_client):
    response = handler.lambda_handler(
        build_direct_event(authorizer=build_lambda_authorizer(user_id="alice", is_admin="yes")),
        None,
    )

    assert_error_response(
        response,
        status_code=400,
        message="requestContext.authorizer.lambda.is_admin must be a boolean when provided.",
    )


# authorization


def test_lambda_handler_allows_public_event_anonymous_rsvp(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item(is_public=True)})
    fake_client.queue_get_item(
        "example-rsvps",
        build_rsvp_key(subject_sk="ANON#browser-token"),
        {},
    )

    response = handler.lambda_handler(
        build_direct_event(authorizer=UNSET, anonymous_token=" browser-token "),
        None,
    )

    body = decode_body(response)
    assert response["statusCode"] == 201
    assert body["item"]["subject"] == {
        "type": "ANON",
        "user_id": None,
        "anonymous": True,
    }


def test_lambda_handler_allows_public_event_authenticated_rsvp(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item(is_public=True)})
    fake_client.queue_get_item(
        "example-rsvps",
        build_rsvp_key(subject_sk="USER#alice"),
        {},
    )

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice")),
        None,
    )

    body = decode_body(response)
    assert response["statusCode"] == 201
    assert body["item"]["subject"] == {
        "type": "USER",
        "user_id": "alice",
        "anonymous": False,
    }


def test_lambda_handler_allows_public_event_anonymous_rsvp_from_lambda_authorizer_shape(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item(is_public=True)})
    fake_client.queue_get_item(
        "example-rsvps",
        build_rsvp_key(subject_sk="ANON#browser-token"),
        {},
    )

    response = handler.lambda_handler(
        build_direct_event(
            authorizer=build_lambda_authorizer(
                user_id=None,
                is_authenticated=False,
                is_admin=False,
            ),
            anonymous_token=" browser-token ",
        ),
        None,
    )

    body = decode_body(response)
    transact_items = fake_client.transact_calls[0]["TransactItems"]
    put_item = transact_items[0]["Put"]["Item"]

    assert response["statusCode"] == 201
    assert body["item"]["subject"] == {
        "type": "ANON",
        "user_id": None,
        "anonymous": True,
    }
    assert put_item["subject_sk"] == {"S": "ANON#browser-token"}
    assert put_item["anonymous_token"] == {"S": "browser-token"}


def test_lambda_handler_allows_public_event_authenticated_rsvp_from_lambda_authorizer_shape(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item(is_public=True)})
    fake_client.queue_get_item(
        "example-rsvps",
        build_rsvp_key(subject_sk="USER#alice"),
        {},
    )

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_lambda_authorizer(user_id="alice")),
        None,
    )

    body = decode_body(response)
    assert response["statusCode"] == 201
    assert body["item"]["subject"] == {
        "type": "USER",
        "user_id": "alice",
        "anonymous": False,
    }


def test_lambda_handler_prefers_api_gateway_body_over_top_level_mutable_fields(fake_client):
    """Body input must win over top-level mutable fields for API Gateway-style requests."""
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item(is_public=True)})
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {})

    response = handler.lambda_handler(
        build_api_gateway_event(
            authorizer=build_authorizer(user_id="alice"),
            attending=True,
            extra={"attending": False},
        ),
        None,
    )

    body = assert_success_status(response, 201)
    transact_items = fake_client.transact_calls[0]["TransactItems"]
    put_item = transact_items[0]["Put"]["Item"]

    assert body["item"]["attending"] is True
    assert put_item["attending"] == {"BOOL": True}


def test_lambda_handler_returns_403_for_protected_event_anonymous_caller(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(is_public=False, requires_admin=False)},
    )

    response = handler.lambda_handler(build_direct_event(authorizer=UNSET, anonymous_token="anon"), None)

    assert_error_response(
        response,
        status_code=403,
        message="Authentication is required to RSVP to this event.",
    )


def test_lambda_handler_allows_protected_event_authenticated_caller(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(is_public=False, requires_admin=False)},
    )
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice")),
        None,
    )

    assert response["statusCode"] == 201


def test_lambda_handler_treats_blank_user_id_as_unauthenticated_for_protected_event(fake_client):
    """Blank user IDs should collapse to anonymous caller behavior after trimming."""
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(is_public=False, requires_admin=False)},
    )

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="   ", is_authenticated=False)),
        None,
    )

    assert_error_response(
        response,
        status_code=403,
        message="Authentication is required to RSVP to this event.",
    )


def test_lambda_handler_returns_403_for_admin_only_event_anonymous_caller(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(is_public=False, requires_admin=True)},
    )

    response = handler.lambda_handler(build_direct_event(authorizer=UNSET, anonymous_token="anon"), None)

    assert_error_response(
        response,
        status_code=403,
        message="Admin privileges are required to RSVP to this event.",
    )


def test_lambda_handler_returns_403_for_admin_only_event_authenticated_non_admin(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(is_public=False, requires_admin=True)},
    )

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice", is_admin=False)),
        None,
    )

    assert_error_response(
        response,
        status_code=403,
        message="Admin privileges are required to RSVP to this event.",
    )


def test_lambda_handler_allows_admin_only_event_authenticated_admin(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(is_public=False, requires_admin=True)},
    )
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#admin-user"), {})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="admin-user", is_admin=True)),
        None,
    )

    body = decode_body(response)
    assert response["statusCode"] == 201
    assert body["item"]["subject"]["type"] == "USER"
    assert body["item"]["subject"]["user_id"] == "admin-user"


def test_lambda_handler_allows_admin_only_event_authenticated_admin_from_lambda_authorizer_shape(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(is_public=False, requires_admin=True)},
    )
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#admin-user"), {})

    response = handler.lambda_handler(
        build_direct_event(
            authorizer=build_lambda_authorizer(
                user_id="admin-user",
                is_authenticated=True,
                is_admin=True,
            )
        ),
        None,
    )

    body = decode_body(response)
    assert response["statusCode"] == 201
    assert body["item"]["subject"]["type"] == "USER"
    assert body["item"]["subject"]["user_id"] == "admin-user"


def test_lambda_handler_accepts_string_admin_flag_for_flat_authorizer_admin_only_event(fake_client):
    """Flat custom-authorizer input still accepts string admin flags for compatibility."""
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(is_public=False, requires_admin=True)},
    )
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#admin-user"), {})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="admin-user", is_admin="true")),
        None,
    )

    body = assert_success_status(response, 201)
    assert body["item"]["subject"]["type"] == "USER"
    assert body["item"]["subject"]["user_id"] == "admin-user"


def test_lambda_handler_returns_400_for_flat_authorizer_is_admin_without_is_authenticated(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(is_public=False, requires_admin=True)},
    )

    response = handler.lambda_handler(
        build_direct_event(authorizer={"is_admin": True}, anonymous_token="anon"),
        None,
    )

    assert_error_response(
        response,
        status_code=400,
        message=(
            "requestContext.authorizer.is_authenticated is required when flat "
            "authorizer caller fields are provided."
        ),
    )


# lifecycle and time gating


def test_lambda_handler_returns_404_when_event_does_not_exist(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {})

    response = handler.lambda_handler(build_direct_event(authorizer=build_authorizer()), None)

    assert_error_response(response, status_code=404, message="Event not found.")


def test_lambda_handler_returns_400_for_cancelled_event(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(status="CANCELLED")},
    )

    response = handler.lambda_handler(build_direct_event(authorizer=build_authorizer()), None)

    assert_error_response(
        response,
        status_code=400,
        message="Cancelled events cannot accept RSVPs.",
    )


def test_lambda_handler_returns_400_for_past_event(fake_client):
    """The locked rule is `event.date <= now`, so an event exactly at now must be rejected."""
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(date=EVENT_DATE_EQUALS_NOW)},
    )

    response = handler.lambda_handler(build_direct_event(authorizer=build_authorizer()), None)

    assert_error_response(response, status_code=400, message="Past events cannot accept RSVPs.")


def test_lambda_handler_returns_500_for_invalid_stored_event_date(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(date="not-a-date")},
    )

    response = handler.lambda_handler(build_direct_event(authorizer=build_authorizer()), None)

    assert_error_response(response, status_code=500, message="Internal server error.")


def test_lambda_handler_returns_500_for_invalid_stored_event_status(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(status="DRAFT")},
    )

    response = handler.lambda_handler(build_direct_event(authorizer=build_authorizer()), None)

    assert_error_response(response, status_code=500, message="Internal server error.")


# create flows


def test_lambda_handler_creates_first_attending_rsvp(fake_client):
    """First attending RSVP should create a canonical RSVP item and increment only attendee counts."""
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(rsvp_total=3, attending_count=2, not_attending_count=1)},
    )
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {})

    response = handler.lambda_handler(
        build_api_gateway_event(authorizer=build_authorizer(user_id="alice")),
        None,
    )

    body = assert_success_status(response, 201)
    assert body["operation"] == "created"
    assert body["item"] == {
        "event_id": EVENT_ID,
        "subject": {
            "type": "USER",
            "user_id": "alice",
            "anonymous": False,
        },
        "attending": True,
        "created_at": FIXED_NOW_ISO,
        "updated_at": FIXED_NOW_ISO,
    }
    assert body["event_summary"] == {
        "status": "ACTIVE",
        "capacity": 10,
        "rsvp_count": 4,
        "attending_count": 3,
        "not_attending_count": 1,
    }

    transact_items = fake_client.transact_calls[0]["TransactItems"]
    put_item = transact_items[0]["Put"]["Item"]
    assert transact_items[0]["Put"]["ConditionExpression"] == "attribute_not_exists(event_pk)"
    assert put_item["subject_sk"] == {"S": "USER#alice"}
    assert put_item["created_at"] == {"S": FIXED_NOW_ISO}
    assert put_item["updated_at"] == {"S": FIXED_NOW_ISO}


def test_lambda_handler_creates_first_not_attending_rsvp(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(rsvp_total=3, attending_count=2, not_attending_count=1)},
    )
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice"), attending=False),
        None,
    )

    body = decode_body(response)
    assert response["statusCode"] == 201
    assert body["operation"] == "created"
    assert body["event_summary"] == {
        "status": "ACTIVE",
        "capacity": 10,
        "rsvp_count": 4,
        "attending_count": 2,
        "not_attending_count": 2,
    }


def test_lambda_handler_trims_anonymous_token_before_storage(fake_client):
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item(is_public=True)})
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="ANON#browser-token"), {})

    response = handler.lambda_handler(
        build_direct_event(authorizer=UNSET, anonymous_token="  browser-token  "),
        None,
    )

    body = decode_body(response)
    transact_items = fake_client.transact_calls[0]["TransactItems"]
    put_item = transact_items[0]["Put"]["Item"]

    assert response["statusCode"] == 201
    assert body["item"]["subject"] == {
        "type": "ANON",
        "user_id": None,
        "anonymous": True,
    }
    assert put_item["subject_sk"] == {"S": "ANON#browser-token"}
    assert put_item["anonymous_token"] == {"S": "browser-token"}


# overwrite flows


def test_lambda_handler_updates_same_value_true_to_true_without_counter_changes(fake_client):
    """Same-value overwrites must refresh timestamps without drifting aggregate counters."""
    current_rsvp = build_rsvp_item(
        subject_sk="USER#alice",
        attending=True,
        created_at="2026-04-01T10:00:00Z",
        updated_at="2026-04-02T10:00:00Z",
    )
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(rsvp_total=3, attending_count=2, not_attending_count=1, capacity=2)},
    )
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {"Item": current_rsvp})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice"), attending=True),
        None,
    )

    body = decode_body(response)
    transact_items = fake_client.transact_calls[0]["TransactItems"]
    put_item = transact_items[0]["Put"]["Item"]
    update_values = transact_items[1]["Update"]["ExpressionAttributeValues"]

    assert response["statusCode"] == 200
    assert body["operation"] == "updated"
    assert body["item"]["created_at"] == "2026-04-01T10:00:00Z"
    assert body["item"]["updated_at"] == FIXED_NOW_ISO
    assert body["event_summary"]["rsvp_count"] == 3
    assert body["event_summary"]["attending_count"] == 2
    assert body["event_summary"]["not_attending_count"] == 1
    assert put_item["created_at"] == {"S": "2026-04-01T10:00:00Z"}
    assert put_item["updated_at"] == {"S": FIXED_NOW_ISO}
    assert update_values[":rsvp_total_delta"] == {"N": "0"}
    assert update_values[":attending_delta"] == {"N": "0"}
    assert update_values[":not_attending_delta"] == {"N": "0"}


def test_lambda_handler_updates_same_value_false_to_false_without_counter_changes(fake_client):
    current_rsvp = build_rsvp_item(
        subject_sk="USER#alice",
        attending=False,
        created_at="2026-04-01T10:00:00Z",
        updated_at="2026-04-02T10:00:00Z",
    )
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item()})
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {"Item": current_rsvp})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice"), attending=False),
        None,
    )

    body = decode_body(response)
    assert response["statusCode"] == 200
    assert body["operation"] == "updated"
    assert body["item"]["created_at"] == "2026-04-01T10:00:00Z"
    assert body["item"]["updated_at"] == FIXED_NOW_ISO
    assert body["event_summary"]["rsvp_count"] == 3
    assert body["event_summary"]["attending_count"] == 2
    assert body["event_summary"]["not_attending_count"] == 1


def test_lambda_handler_flips_true_to_false_and_updates_counters(fake_client):
    current_rsvp = build_rsvp_item(subject_sk="USER#alice", attending=True)
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item()})
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {"Item": current_rsvp})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice"), attending=False),
        None,
    )

    body = decode_body(response)
    assert response["statusCode"] == 200
    assert body["operation"] == "updated"
    assert body["event_summary"]["rsvp_count"] == 3
    assert body["event_summary"]["attending_count"] == 1
    assert body["event_summary"]["not_attending_count"] == 2


def test_lambda_handler_flips_false_to_true_and_updates_counters(fake_client):
    current_rsvp = build_rsvp_item(subject_sk="USER#alice", attending=False)
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item()})
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {"Item": current_rsvp})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice"), attending=True),
        None,
    )

    body = decode_body(response)
    assert response["statusCode"] == 200
    assert body["operation"] == "updated"
    assert body["event_summary"]["rsvp_count"] == 3
    assert body["event_summary"]["attending_count"] == 3
    assert body["event_summary"]["not_attending_count"] == 0


# capacity flows


def test_lambda_handler_returns_400_for_full_capacity_on_first_attending_create(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(capacity=2, attending_count=2)},
    )
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice"), attending=True),
        None,
    )

    assert_error_response(response, status_code=400, message="Event is at full capacity.")


def test_lambda_handler_returns_400_for_full_capacity_on_false_to_true_flip(fake_client):
    current_rsvp = build_rsvp_item(subject_sk="USER#alice", attending=False)
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(capacity=2, attending_count=2)},
    )
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {"Item": current_rsvp})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice"), attending=True),
        None,
    )

    assert_error_response(response, status_code=400, message="Event is at full capacity.")


def test_lambda_handler_allows_first_not_attending_create_when_event_is_full(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(capacity=2, attending_count=2)},
    )
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice"), attending=False),
        None,
    )

    assert response["statusCode"] == 201


def test_lambda_handler_allows_attending_create_when_capacity_is_unlimited(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(capacity=None)},
    )
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice"), attending=True),
        None,
    )

    assert response["statusCode"] == 201
    assert decode_body(response)["event_summary"]["capacity"] is None


def test_lambda_handler_allows_same_value_true_to_true_even_when_full(fake_client):
    current_rsvp = build_rsvp_item(subject_sk="USER#alice", attending=True)
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(capacity=2, attending_count=2)},
    )
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {"Item": current_rsvp})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice"), attending=True),
        None,
    )

    assert response["statusCode"] == 200


def test_lambda_handler_allows_true_to_false_even_when_full(fake_client):
    current_rsvp = build_rsvp_item(subject_sk="USER#alice", attending=True)
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(capacity=2, attending_count=2)},
    )
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {"Item": current_rsvp})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice"), attending=False),
        None,
    )

    assert response["statusCode"] == 200


# transaction builder


@pytest.mark.parametrize(
    ("previous_attending", "new_attending", "expected"),
    [
        (None, True, {"operation": "created", "rsvp_total_delta": 1, "attending_count_delta": 1, "not_attending_count_delta": 0, "seat_consuming_write": True}),
        (None, False, {"operation": "created", "rsvp_total_delta": 1, "attending_count_delta": 0, "not_attending_count_delta": 1, "seat_consuming_write": False}),
        (True, True, {"operation": "updated", "rsvp_total_delta": 0, "attending_count_delta": 0, "not_attending_count_delta": 0, "seat_consuming_write": False}),
        (False, False, {"operation": "updated", "rsvp_total_delta": 0, "attending_count_delta": 0, "not_attending_count_delta": 0, "seat_consuming_write": False}),
        (True, False, {"operation": "updated", "rsvp_total_delta": 0, "attending_count_delta": -1, "not_attending_count_delta": 1, "seat_consuming_write": False}),
        (False, True, {"operation": "updated", "rsvp_total_delta": 0, "attending_count_delta": 1, "not_attending_count_delta": -1, "seat_consuming_write": True}),
    ],
)
def test_calculate_rsvp_change_returns_locked_delta_matrix(previous_attending, new_attending, expected):
    """Keep the six-case delta matrix explicit because it is the load-bearing RSVP math."""
    result = handler._calculate_rsvp_change(
        previous_attending=previous_attending,
        new_attending=new_attending,
    )

    for key, value in expected.items():
        assert result[key] == value


def test_build_rsvp_put_transaction_item_uses_non_existence_condition_for_create():
    result = handler._build_rsvp_put_transaction_item(
        table_name="example-rsvps",
        rsvp_item=build_rsvp_item(),
        current_rsvp=None,
    )

    assert result["Put"]["TableName"] == "example-rsvps"
    assert result["Put"]["ConditionExpression"] == "attribute_not_exists(event_pk)"
    assert "ExpressionAttributeValues" not in result["Put"]


def test_build_rsvp_put_transaction_item_uses_previous_state_condition_for_update():
    """Update writes must pin previous state so concurrent same-subject requests cannot drift counters."""
    current_rsvp = {
        "attending": False,
        "created_at": "2026-04-01T10:00:00Z",
    }

    result = handler._build_rsvp_put_transaction_item(
        table_name="example-rsvps",
        rsvp_item=build_rsvp_item(attending=True),
        current_rsvp=current_rsvp,
    )

    condition = result["Put"]["ConditionExpression"]
    values = result["Put"]["ExpressionAttributeValues"]

    assert "attribute_exists(event_pk)" in condition
    assert "attribute_exists(subject_sk)" in condition
    assert "attending = :previous_attending" in condition
    assert "created_at = :previous_created_at" in condition
    assert values == {
        ":previous_attending": {"BOOL": False},
        ":previous_created_at": {"S": "2026-04-01T10:00:00Z"},
    }


def test_build_event_update_transaction_item_omits_attending_name_for_non_seat_consuming_write():
    """Non-seat-consuming writes must not send unused DynamoDB expression names."""
    result = handler._build_event_update_transaction_item(
        table_name="example-events",
        event_key=build_event_key(),
        event_state={
            "capacity": 10,
        },
        change={
            "rsvp_total_delta": 0,
            "attending_count_delta": 0,
            "not_attending_count_delta": 0,
            "seat_consuming_write": False,
        },
    )

    assert result["Update"]["ExpressionAttributeNames"] == {
        "#status": "status",
    }


# transaction failure reclassification


def test_lambda_handler_returns_404_when_transaction_failure_reclassifies_to_missing_event(fake_client):
    fake_client.transaction_error = transaction_cancelled_error()
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item()},
        {},
    )
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice")),
        None,
    )

    assert_error_response(response, status_code=404, message="Event not found.")


def test_lambda_handler_returns_400_when_transaction_failure_reclassifies_to_cancelled_event(fake_client):
    """After a cancelled transaction, the handler re-reads only the event item to classify the failure."""
    fake_client.transaction_error = transaction_cancelled_error()
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item()},
        {"Item": build_event_item(status="CANCELLED")},
    )
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice")),
        None,
    )

    assert_error_response(
        response,
        status_code=400,
        message="Cancelled events cannot accept RSVPs.",
    )


def test_lambda_handler_returns_400_when_transaction_failure_reclassifies_to_full_capacity(fake_client):
    fake_client.transaction_error = transaction_cancelled_error()
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item(capacity=3, attending_count=2)},
        {"Item": build_event_item(capacity=3, attending_count=3)},
    )
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice"), attending=True),
        None,
    )

    assert_error_response(response, status_code=400, message="Event is at full capacity.")


def test_lambda_handler_returns_500_when_transaction_failure_has_no_known_business_explanation(fake_client):
    fake_client.transaction_error = transaction_cancelled_error()
    fake_client.queue_get_item(
        "example-events",
        build_event_key(),
        {"Item": build_event_item()},
        {"Item": build_event_item()},
    )
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="USER#alice"), {})

    response = handler.lambda_handler(
        build_direct_event(authorizer=build_authorizer(user_id="alice")),
        None,
    )

    assert_error_response(response, status_code=500, message="Internal server error.")


# response contract


def test_lambda_handler_returns_wrapped_success_response_without_internal_fields(fake_client):
    """Success responses must expose the public RSVP contract, not raw DynamoDB storage fields."""
    fake_client.queue_get_item("example-events", build_event_key(), {"Item": build_event_item(is_public=True)})
    fake_client.queue_get_item("example-rsvps", build_rsvp_key(subject_sk="ANON#guest-123"), {})

    response = handler.lambda_handler(
        build_direct_event(authorizer=UNSET, anonymous_token="guest-123"),
        None,
    )

    body = decode_body(response)
    assert set(response.keys()) == {"statusCode", "headers", "body"}
    assert response["headers"] == {"Content-Type": "application/json"}
    assert set(body.keys()) == {"item", "event_summary", "operation"}
    assert body["item"]["event_id"] == EVENT_ID
    assert body["item"]["attending"] is True
    assert body["item"]["created_at"] == FIXED_NOW_ISO
    assert body["item"]["updated_at"] == FIXED_NOW_ISO
    assert body["item"]["subject"] == {
        "type": "ANON",
        "user_id": None,
        "anonymous": True,
    }
    assert body["event_summary"] == {
        "status": "ACTIVE",
        "capacity": 10,
        "rsvp_count": 4,
        "attending_count": 3,
        "not_attending_count": 1,
    }
    assert "subject_sk" not in body["item"]
    assert "event_pk" not in body["item"]
    assert "public_upcoming_gsi_pk" not in body["item"]
    assert "public_upcoming_gsi_sk" not in body["item"]


def test_lambda_handler_prefers_path_parameters_over_top_level_event_id(fake_client):
    fake_client.queue_get_item(
        "example-events",
        build_event_key("22222222-2222-2222-2222-222222222222"),
        {"Item": build_event_item(event_id="22222222-2222-2222-2222-222222222222")},
    )
    fake_client.queue_get_item(
        "example-rsvps",
        build_rsvp_key(event_id="22222222-2222-2222-2222-222222222222", subject_sk="USER#alice"),
        {},
    )

    response = handler.lambda_handler(
        build_api_gateway_event(
            event_id="22222222-2222-2222-2222-222222222222",
            top_level_event_id="should-not-be-used",
            authorizer=build_authorizer(user_id="alice"),
        ),
        None,
    )

    assert response["statusCode"] == 201
    assert fake_client.get_calls[0]["Key"] == build_event_key("22222222-2222-2222-2222-222222222222")


# deserialization correctness


def test_deserialize_event_item_raises_for_invalid_shape():
    with pytest.raises(handler.EventStateError):
        handler._deserialize_event_item({"status": {"S": "ACTIVE"}})


def test_deserialize_rsvp_item_raises_for_invalid_shape():
    with pytest.raises(handler.RsvpStateError):
        handler._deserialize_rsvp_item({"event_pk": {"S": f"EVENT#{EVENT_ID}"}})


def test_deserialize_event_date_raises_for_non_utc_timestamp():
    with pytest.raises(handler.EventStateError):
        handler._deserialize_event_date({"S": "2026-06-15T00:00:00+02:00"})


def test_deserialize_event_date_raises_for_naive_timestamp():
    """Stored canonical event datetimes must always be timezone-aware UTC values."""
    with pytest.raises(handler.EventStateError):
        handler._deserialize_event_date({"S": "2026-06-15T00:00:00"})
