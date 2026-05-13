import json

import pytest
from botocore.exceptions import ClientError

from lambdas.notification_planner import handler


EVENT_ID = "11111111-1111-1111-1111-111111111111"


def build_eventbridge_event(
    *,
    detail_type: str = "event.updated",
    event_id: str = EVENT_ID,
    title: str = "Platform Launch Event",
    event_detail_path: str = f"/app/events/{EVENT_ID}",
    occurred_at: str = "2026-05-12T10:00:00Z",
    changed_fields: list[str] | None = None,
    detail_overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    detail: dict[str, object] = {
        "event_id": event_id,
        "title": title,
        "event_detail_path": event_detail_path,
        "occurred_at": occurred_at,
    }

    if detail_type == "event.updated":
        detail["changed_fields"] = changed_fields if changed_fields is not None else ["date", "location"]

    if detail_overrides:
        detail.update(detail_overrides)

    return {
        "version": "0",
        "id": "eventbridge-message-id",
        "detail-type": detail_type,
        "source": "aws-serverless-events-platform",
        "detail": detail,
    }


def build_sqs_record(*, message_id: str, body: object) -> dict[str, object]:
    return {
        "messageId": message_id,
        "body": json.dumps(body, separators=(",", ":"), sort_keys=True),
    }


def build_sqs_event(*records: dict[str, object]) -> dict[str, object]:
    return {"Records": list(records)}


def build_rsvp_item(
    *,
    event_id: str = EVENT_ID,
    subject_type: str = "USER",
    user_id: str | None = "alice-sub",
    attending: bool = True,
    anonymous_token: str | None = None,
) -> dict[str, object]:
    item: dict[str, object] = {
        "event_pk": {"S": f"EVENT#{event_id}"},
        "subject_type": {"S": subject_type},
        "attending": {"BOOL": attending},
    }

    if user_id is not None:
        item["user_id"] = {"S": user_id}
    if anonymous_token is not None:
        item["anonymous_token"] = {"S": anonymous_token}

    return item


def decode_sent_messages(fake_sqs_client: "FakeSQSClient") -> list[dict[str, object]]:
    return [json.loads(call["MessageBody"]) for call in fake_sqs_client.send_calls]


class FakeDynamoDBClient:
    def __init__(self) -> None:
        self.query_calls: list[dict[str, object]] = []
        self.query_responses: list[dict[str, object] | Exception] = []

    def queue_query(self, *responses: dict[str, object] | Exception) -> None:
        self.query_responses.extend(responses)

    def query(self, **kwargs: object) -> dict[str, object]:
        self.query_calls.append(dict(kwargs))
        if not self.query_responses:
            return {"Items": []}

        response = self.query_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return dict(response)


class FakeSQSClient:
    def __init__(self) -> None:
        self.send_calls: list[dict[str, object]] = []
        self.fail_on_send_number: int | None = None
        self.send_attempts = 0

    def send_message(self, **kwargs: object) -> dict[str, object]:
        self.send_attempts += 1
        if self.fail_on_send_number is not None and self.send_attempts == self.fail_on_send_number:
            raise ClientError(
                error_response={"Error": {"Code": "InternalError", "Message": "send failed"}},
                operation_name="SendMessage",
            )

        self.send_calls.append(dict(kwargs))
        return {"MessageId": f"sent-{len(self.send_calls)}"}


@pytest.fixture
def fake_clients(monkeypatch) -> tuple[FakeDynamoDBClient, FakeSQSClient]:
    dynamodb_client = FakeDynamoDBClient()
    sqs_client = FakeSQSClient()

    monkeypatch.setenv("RSVPS_TABLE_NAME", "example-rsvps")
    monkeypatch.setenv("NOTIFICATION_EMAIL_QUEUE_URL", "https://sqs.example/notification-email")
    monkeypatch.setattr(handler, "_get_dynamodb_client", lambda: dynamodb_client)
    monkeypatch.setattr(handler, "_get_sqs_client", lambda: sqs_client)

    return dynamodb_client, sqs_client


def test_lambda_handler_enqueues_updated_messages_for_authenticated_true_and_false_rsvps(fake_clients):
    dynamodb_client, sqs_client = fake_clients
    dynamodb_client.queue_query(
        {
            "Items": [
                build_rsvp_item(user_id="alice-sub", attending=True),
                build_rsvp_item(user_id="bob-sub", attending=False),
                build_rsvp_item(
                    subject_type="ANON",
                    user_id=None,
                    attending=True,
                    anonymous_token="browser-token",
                ),
            ]
        }
    )

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_eventbridge_event(changed_fields=["date", "location"]),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": []}
    assert dynamodb_client.query_calls == [
        {
            "TableName": "example-rsvps",
            "KeyConditionExpression": "event_pk = :event_pk",
            "ExpressionAttributeValues": {
                ":event_pk": {"S": f"EVENT#{EVENT_ID}"},
            },
            "ScanIndexForward": True,
        }
    ]
    assert [call["QueueUrl"] for call in sqs_client.send_calls] == [
        "https://sqs.example/notification-email",
        "https://sqs.example/notification-email",
    ]
    assert decode_sent_messages(sqs_client) == [
        {
            "changed_fields": ["date", "location"],
            "event_detail_path": f"/app/events/{EVENT_ID}",
            "event_id": EVENT_ID,
            "event_title": "Platform Launch Event",
            "notification_type": "event.updated",
            "occurred_at": "2026-05-12T10:00:00Z",
            "recipient_user_id": "alice-sub",
        },
        {
            "changed_fields": ["date", "location"],
            "event_detail_path": f"/app/events/{EVENT_ID}",
            "event_id": EVENT_ID,
            "event_title": "Platform Launch Event",
            "notification_type": "event.updated",
            "occurred_at": "2026-05-12T10:00:00Z",
            "recipient_user_id": "bob-sub",
        },
    ]

    for message in decode_sent_messages(sqs_client):
        assert "email" not in message
        assert "username" not in message
        assert "anonymous_token" not in message
        assert "event_pk" not in message
        assert "subject_sk" not in message


def test_lambda_handler_enqueues_cancelled_messages_without_changed_fields(fake_clients):
    dynamodb_client, sqs_client = fake_clients
    dynamodb_client.queue_query(
        {
            "Items": [
                build_rsvp_item(user_id="alice-sub", attending=True),
            ]
        }
    )

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_eventbridge_event(detail_type="event.cancelled"),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": []}
    assert decode_sent_messages(sqs_client) == [
        {
            "event_detail_path": f"/app/events/{EVENT_ID}",
            "event_id": EVENT_ID,
            "event_title": "Platform Launch Event",
            "notification_type": "event.cancelled",
            "occurred_at": "2026-05-12T10:00:00Z",
            "recipient_user_id": "alice-sub",
        }
    ]
    assert "changed_fields" not in decode_sent_messages(sqs_client)[0]


def test_lambda_handler_ignores_unsupported_event_types_successfully(fake_clients):
    dynamodb_client, sqs_client = fake_clients

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_eventbridge_event(detail_type="event.created"),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": []}
    assert dynamodb_client.query_calls == []
    assert sqs_client.send_calls == []


def test_lambda_handler_returns_partial_failure_for_one_malformed_supported_record(fake_clients):
    dynamodb_client, sqs_client = fake_clients
    dynamodb_client.queue_query(
        {
            "Items": [
                build_rsvp_item(user_id="alice-sub"),
            ]
        }
    )

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="bad-message",
                body=build_eventbridge_event(detail_overrides={"event_id": ""}),
            ),
            build_sqs_record(
                message_id="good-message",
                body=build_eventbridge_event(),
            ),
        ),
        None,
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "bad-message"}]}
    assert len(dynamodb_client.query_calls) == 1
    assert decode_sent_messages(sqs_client)[0]["recipient_user_id"] == "alice-sub"


def test_lambda_handler_paginates_rsvp_query_results(fake_clients):
    dynamodb_client, sqs_client = fake_clients
    dynamodb_client.queue_query(
        {
            "Items": [
                build_rsvp_item(user_id="alice-sub"),
            ],
            "LastEvaluatedKey": {
                "event_pk": {"S": f"EVENT#{EVENT_ID}"},
                "subject_sk": {"S": "USER#alice-sub"},
            },
        },
        {
            "Items": [
                build_rsvp_item(user_id="bob-sub", attending=False),
            ],
        },
    )

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_eventbridge_event(),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": []}
    assert len(dynamodb_client.query_calls) == 2
    assert dynamodb_client.query_calls[1]["ExclusiveStartKey"] == {
        "event_pk": {"S": f"EVENT#{EVENT_ID}"},
        "subject_sk": {"S": "USER#alice-sub"},
    }
    assert [message["recipient_user_id"] for message in decode_sent_messages(sqs_client)] == [
        "alice-sub",
        "bob-sub",
    ]


def test_lambda_handler_returns_success_when_event_has_no_authenticated_rsvps(fake_clients):
    dynamodb_client, sqs_client = fake_clients
    dynamodb_client.queue_query(
        {
            "Items": [
                build_rsvp_item(
                    subject_type="ANON",
                    user_id=None,
                    anonymous_token="browser-token",
                ),
            ]
        }
    )

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_eventbridge_event(),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": []}
    assert len(dynamodb_client.query_calls) == 1
    assert sqs_client.send_calls == []


def test_lambda_handler_marks_record_failed_when_user_rsvp_is_malformed(fake_clients):
    dynamodb_client, sqs_client = fake_clients
    dynamodb_client.queue_query(
        {
            "Items": [
                build_rsvp_item(user_id=None),
            ]
        }
    )

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_eventbridge_event(),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "message-1"}]}
    assert sqs_client.send_calls == []


def test_lambda_handler_marks_only_failed_record_when_sqs_send_fails(fake_clients):
    dynamodb_client, sqs_client = fake_clients
    sqs_client.fail_on_send_number = 1
    dynamodb_client.queue_query(
        {
            "Items": [
                build_rsvp_item(user_id="alice-sub"),
            ]
        },
        {
            "Items": [
                build_rsvp_item(
                    event_id="22222222-2222-2222-2222-222222222222",
                    user_id="bob-sub",
                ),
            ]
        },
    )

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="failed-message",
                body=build_eventbridge_event(event_id=EVENT_ID),
            ),
            build_sqs_record(
                message_id="good-message",
                body=build_eventbridge_event(event_id="22222222-2222-2222-2222-222222222222"),
            ),
        ),
        None,
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "failed-message"}]}
    assert [message["recipient_user_id"] for message in decode_sent_messages(sqs_client)] == ["bob-sub"]


def test_lambda_handler_marks_record_failed_when_dynamodb_query_fails(fake_clients):
    dynamodb_client, sqs_client = fake_clients
    dynamodb_client.queue_query(
        ClientError(
            error_response={"Error": {"Code": "InternalServerError", "Message": "query failed"}},
            operation_name="Query",
        )
    )

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_eventbridge_event(),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "message-1"}]}
    assert sqs_client.send_calls == []
