import json

import pytest
from botocore.exceptions import ClientError

from lambdas.notification_sender import handler


EVENT_ID = "11111111-1111-1111-1111-111111111111"
RECIPIENT_USER_ID = "3304b842-8081-7092-7c59-162ca076d352"


def build_recipient_message(
    *,
    notification_type: str = "event.updated",
    event_id: str = EVENT_ID,
    event_title: str = "Platform Launch Event",
    event_detail_path: str = f"/app/events/{EVENT_ID}",
    recipient_user_id: str = RECIPIENT_USER_ID,
    changed_fields: list[str] | None = None,
    message_overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    message: dict[str, object] = {
        "notification_type": notification_type,
        "event_id": event_id,
        "event_title": event_title,
        "event_detail_path": event_detail_path,
        "recipient_user_id": recipient_user_id,
        "occurred_at": "2026-05-12T10:00:00Z",
    }

    if notification_type == "event.updated":
        message["changed_fields"] = changed_fields if changed_fields is not None else ["date", "location"]

    if message_overrides:
        message.update(message_overrides)

    return message


def build_sqs_record(*, message_id: str, body: object) -> dict[str, object]:
    return {
        "messageId": message_id,
        "body": json.dumps(body, separators=(",", ":"), sort_keys=True),
    }


def build_sqs_event(*records: dict[str, object]) -> dict[str, object]:
    return {"Records": list(records)}


def build_cognito_user(
    *,
    email: str = "recipient@example.com",
    sub: str = RECIPIENT_USER_ID,
) -> dict[str, object]:
    return {
        "Username": "cognito-username",
        "Attributes": [
            {"Name": "sub", "Value": sub},
            {"Name": "email", "Value": email},
        ],
    }


def decode_template_data(fake_ses_client: "FakeSESClient") -> list[dict[str, object]]:
    return [json.loads(call["TemplateData"]) for call in fake_ses_client.send_calls]


class FakeCognitoClient:
    def __init__(self) -> None:
        self.list_users_calls: list[dict[str, object]] = []
        self.list_users_responses: list[dict[str, object] | Exception] = []

    def queue_list_users(self, *responses: dict[str, object] | Exception) -> None:
        self.list_users_responses.extend(responses)

    def list_users(self, **kwargs: object) -> dict[str, object]:
        self.list_users_calls.append(dict(kwargs))
        if not self.list_users_responses:
            return {"Users": [build_cognito_user()]}

        response = self.list_users_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return dict(response)


class FakeSESClient:
    def __init__(self) -> None:
        self.send_calls: list[dict[str, object]] = []
        self.fail_on_send_number: int | None = None
        self.send_attempts = 0

    def send_templated_email(self, **kwargs: object) -> dict[str, object]:
        self.send_attempts += 1
        if self.fail_on_send_number is not None and self.send_attempts == self.fail_on_send_number:
            raise ClientError(
                error_response={"Error": {"Code": "InternalError", "Message": "send failed"}},
                operation_name="SendTemplatedEmail",
            )

        self.send_calls.append(dict(kwargs))
        return {"MessageId": f"sent-{len(self.send_calls)}"}


@pytest.fixture
def fake_clients(monkeypatch) -> tuple[FakeCognitoClient, FakeSESClient]:
    cognito_client = FakeCognitoClient()
    ses_client = FakeSESClient()

    monkeypatch.setenv("COGNITO_USER_POOL_ID", "eu-central-1_example")
    monkeypatch.setenv("SES_SOURCE_EMAIL", "aws.serverless.events.platform@example.com")
    monkeypatch.setenv("SES_TEMPLATE_EVENT_UPDATED", "platform-dev-event-updated")
    monkeypatch.setenv("SES_TEMPLATE_EVENT_CANCELLED", "platform-dev-event-cancelled")
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://d111111abcdef8.cloudfront.net")
    monkeypatch.setattr(handler, "_get_cognito_client", lambda: cognito_client)
    monkeypatch.setattr(handler, "_get_ses_client", lambda: ses_client)

    return cognito_client, ses_client


def test_lambda_handler_sends_updated_email_with_safe_template_data(fake_clients):
    cognito_client, ses_client = fake_clients

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_recipient_message(
                    event_title='Platform <Launch> & "Demo"',
                    changed_fields=["date", "location<script>"],
                ),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": []}
    assert cognito_client.list_users_calls == [
        {
            "UserPoolId": "eu-central-1_example",
            "Filter": f'sub = "{RECIPIENT_USER_ID}"',
            "Limit": 2,
        }
    ]
    assert ses_client.send_calls == [
        {
            "Source": "aws.serverless.events.platform@example.com",
            "Destination": {"ToAddresses": ["recipient@example.com"]},
            "Template": "platform-dev-event-updated",
            "TemplateData": ses_client.send_calls[0]["TemplateData"],
        }
    ]
    assert decode_template_data(ses_client) == [
        {
            "changed_fields": ["date", "location&lt;script&gt;"],
            "event_title": "Platform &lt;Launch&gt; &amp; &quot;Demo&quot;",
            "event_url": f"https://d111111abcdef8.cloudfront.net/app/events/{EVENT_ID}",
        }
    ]


def test_lambda_handler_sends_cancelled_email_without_changed_fields(fake_clients):
    _cognito_client, ses_client = fake_clients

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_recipient_message(notification_type="event.cancelled"),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": []}
    assert ses_client.send_calls[0]["Template"] == "platform-dev-event-cancelled"
    assert decode_template_data(ses_client) == [
        {
            "event_title": "Platform Launch Event",
            "event_url": f"https://d111111abcdef8.cloudfront.net/app/events/{EVENT_ID}",
        }
    ]


def test_lambda_handler_uses_cognito_email_instead_of_payload_email(fake_clients):
    cognito_client, ses_client = fake_clients
    cognito_client.queue_list_users({"Users": [build_cognito_user(email="current@example.com")]})

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_recipient_message(
                    message_overrides={"email": "attacker@example.com"},
                ),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": []}
    assert ses_client.send_calls[0]["Destination"] == {"ToAddresses": ["current@example.com"]}


def test_lambda_handler_marks_record_failed_when_cognito_returns_no_users(fake_clients):
    cognito_client, ses_client = fake_clients
    cognito_client.queue_list_users({"Users": []})

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_recipient_message(),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "message-1"}]}
    assert ses_client.send_calls == []


def test_lambda_handler_marks_record_failed_when_cognito_returns_multiple_users(fake_clients):
    cognito_client, ses_client = fake_clients
    cognito_client.queue_list_users(
        {
            "Users": [
                build_cognito_user(email="first@example.com"),
                build_cognito_user(email="second@example.com"),
            ]
        }
    )

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_recipient_message(),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "message-1"}]}
    assert ses_client.send_calls == []


def test_lambda_handler_marks_record_failed_when_cognito_user_has_no_email(fake_clients):
    cognito_client, ses_client = fake_clients
    cognito_client.queue_list_users({"Users": [{"Attributes": [{"Name": "sub", "Value": RECIPIENT_USER_ID}]}]})

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_recipient_message(),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "message-1"}]}
    assert ses_client.send_calls == []


def test_lambda_handler_marks_record_failed_when_cognito_email_is_malformed(fake_clients):
    cognito_client, ses_client = fake_clients
    cognito_client.queue_list_users({"Users": [build_cognito_user(email="not an email")]})

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_recipient_message(),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "message-1"}]}
    assert ses_client.send_calls == []


def test_lambda_handler_marks_record_failed_for_malformed_json(fake_clients):
    _cognito_client, ses_client = fake_clients

    response = handler.lambda_handler(
        build_sqs_event(
            {
                "messageId": "message-1",
                "body": "{not-json",
            }
        ),
        None,
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "message-1"}]}
    assert ses_client.send_calls == []


def test_lambda_handler_marks_record_failed_for_unsupported_notification_type(fake_clients):
    _cognito_client, ses_client = fake_clients

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_recipient_message(notification_type="event.created"),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "message-1"}]}
    assert ses_client.send_calls == []


def test_lambda_handler_marks_record_failed_for_unsafe_event_detail_path(fake_clients):
    _cognito_client, ses_client = fake_clients

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_recipient_message(event_detail_path=f"/app/events/{EVENT_ID}\" onclick=\"bad"),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "message-1"}]}
    assert ses_client.send_calls == []


def test_lambda_handler_marks_record_failed_when_frontend_base_url_is_not_https(fake_clients, monkeypatch):
    _cognito_client, ses_client = fake_clients
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://example.com")

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_recipient_message(),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "message-1"}]}
    assert ses_client.send_calls == []


def test_lambda_handler_marks_only_failed_record_when_ses_send_fails(fake_clients):
    cognito_client, ses_client = fake_clients
    ses_client.fail_on_send_number = 1
    cognito_client.queue_list_users(
        {"Users": [build_cognito_user(email="first@example.com", sub="first-sub")]},
        {"Users": [build_cognito_user(email="second@example.com", sub="second-sub")]},
    )

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="failed-message",
                body=build_recipient_message(recipient_user_id="first-sub"),
            ),
            build_sqs_record(
                message_id="good-message",
                body=build_recipient_message(recipient_user_id="second-sub"),
            ),
        ),
        None,
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "failed-message"}]}
    assert ses_client.send_attempts == 2
    assert ses_client.send_calls[0]["Destination"] == {"ToAddresses": ["second@example.com"]}


def test_lambda_handler_marks_record_failed_when_cognito_lookup_fails(fake_clients):
    cognito_client, ses_client = fake_clients
    cognito_client.queue_list_users(
        ClientError(
            error_response={"Error": {"Code": "InternalError", "Message": "lookup failed"}},
            operation_name="ListUsers",
        )
    )

    response = handler.lambda_handler(
        build_sqs_event(
            build_sqs_record(
                message_id="message-1",
                body=build_recipient_message(),
            )
        ),
        None,
    )

    assert response == {"batchItemFailures": [{"itemIdentifier": "message-1"}]}
    assert ses_client.send_calls == []
