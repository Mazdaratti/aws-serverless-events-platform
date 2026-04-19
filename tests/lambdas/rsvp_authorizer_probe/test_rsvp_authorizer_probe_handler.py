import json

from lambdas.rsvp_authorizer_probe import handler


def _parse_body(response: dict[str, object]) -> dict[str, object]:
    body = response["body"]
    assert isinstance(body, str)
    return json.loads(body)


def test_lambda_handler_returns_400_for_non_object_event():
    response = handler.lambda_handler("bad-event", None)

    assert response["statusCode"] == 400
    assert response["headers"] == {"Content-Type": "application/json"}
    assert _parse_body(response) == {
        "message": "Event payload must be a JSON object."
    }


def test_lambda_handler_returns_anonymous_probe_result_without_request_context():
    response = handler.lambda_handler({}, None)

    assert response["statusCode"] == 200
    assert response["headers"] == {"Content-Type": "application/json"}
    assert _parse_body(response) == {
        "authorizer": None,
        "normalized_caller": {
            "user_id": None,
            "is_authenticated": False,
            "is_admin": False,
        },
    }


def test_lambda_handler_echoes_and_normalizes_flat_authorizer_context():
    event = {
        "requestContext": {
            "authorizer": {
                "user_id": "user-123",
                "is_authenticated": True,
                "is_admin": False,
            }
        }
    }

    response = handler.lambda_handler(event, None)

    assert response["statusCode"] == 200
    assert response["headers"] == {"Content-Type": "application/json"}
    assert _parse_body(response) == {
        "authorizer": {
            "user_id": "user-123",
            "is_authenticated": True,
            "is_admin": False,
        },
        "normalized_caller": {
            "user_id": "user-123",
            "is_authenticated": True,
            "is_admin": False,
        },
    }


def test_lambda_handler_returns_400_for_malformed_request_context():
    response = handler.lambda_handler({"requestContext": "bad-shape"}, None)

    assert response["statusCode"] == 400
    assert response["headers"] == {"Content-Type": "application/json"}
    assert _parse_body(response) == {
        "message": "requestContext must be an object when provided."
    }


def test_lambda_handler_returns_400_for_malformed_authorizer_context():
    response = handler.lambda_handler(
        {
            "requestContext": {
                "authorizer": "bad-shape",
            }
        },
        None,
    )

    assert response["statusCode"] == 400
    assert response["headers"] == {"Content-Type": "application/json"}
    assert _parse_body(response) == {
        "message": "requestContext.authorizer must be an object when provided."
    }
