from pathlib import Path
import sys
from urllib.error import URLError

import pytest

VENDOR_PATH = Path(__file__).resolve().parents[3] / "lambdas" / "rsvp_authorizer" / "vendor"
if str(VENDOR_PATH) not in sys.path:
    sys.path.insert(0, str(VENDOR_PATH))

from jwt import InvalidTokenError

from lambdas.rsvp_authorizer import handler


UNSET = object()


def _authorizer_event(authorization=UNSET):
    event: dict[str, object] = {}

    if authorization is UNSET:
        return event

    event["headers"] = {
        "Authorization": authorization,
    }
    return event


@pytest.fixture(autouse=True)
def auth_env(monkeypatch):
    monkeypatch.setenv("COGNITO_ISSUER", "https://cognito-idp.eu-central-1.amazonaws.com/eu-central-1_example")
    monkeypatch.setenv("COGNITO_APP_CLIENT_ID", "example-client-id")
    monkeypatch.setenv("COGNITO_ADMIN_GROUP_NAME", "admin")


def test_lambda_handler_allows_anonymous_request_when_authorization_header_is_missing():
    response = handler.lambda_handler({}, None)

    assert response == {
        "isAuthorized": True,
        "context": {
            "user_id": None,
            "is_authenticated": False,
            "is_admin": False,
        },
    }


def test_lambda_handler_denies_blank_authorization_header():
    response = handler.lambda_handler(_authorizer_event("   "), None)

    assert response == {
        "isAuthorized": False,
    }


def test_lambda_handler_denies_non_string_authorization_header():
    response = handler.lambda_handler(_authorizer_event(123), None)

    assert response == {
        "isAuthorized": False,
    }


def test_lambda_handler_denies_non_bearer_authorization_header():
    response = handler.lambda_handler(_authorizer_event("Basic abc123"), None)

    assert response == {
        "isAuthorized": False,
    }


def test_lambda_handler_denies_empty_bearer_token():
    response = handler.lambda_handler(_authorizer_event("Bearer   "), None)

    assert response == {
        "isAuthorized": False,
    }


def test_lambda_handler_allows_authenticated_non_admin_request(monkeypatch):
    seen: dict[str, str] = {}

    def _decode(token: str):
        seen["token"] = token
        return {
            "sub": "alice-sub",
            "cognito:groups": ["member"],
        }

    monkeypatch.setattr(handler, "_decode_and_validate_token", _decode)

    response = handler.lambda_handler(_authorizer_event("Bearer good-token"), None)

    assert seen["token"] == "good-token"
    assert response == {
        "isAuthorized": True,
        "context": {
            "user_id": "alice-sub",
            "is_authenticated": True,
            "is_admin": False,
        },
    }


def test_lambda_handler_allows_authenticated_admin_request(monkeypatch):
    seen: dict[str, str] = {}

    def _decode(token: str):
        seen["token"] = token
        return {
            "sub": "admin-sub",
            "cognito:groups": ["admin", "organizer"],
        }

    monkeypatch.setattr(handler, "_decode_and_validate_token", _decode)

    response = handler.lambda_handler(_authorizer_event("Bearer admin-token"), None)

    assert seen["token"] == "admin-token"
    assert response == {
        "isAuthorized": True,
        "context": {
            "user_id": "admin-sub",
            "is_authenticated": True,
            "is_admin": True,
        },
    }


def test_lambda_handler_denies_invalid_token(monkeypatch):
    def _raise_invalid(_token: str):
        raise InvalidTokenError("bad token")

    monkeypatch.setattr(handler, "_decode_and_validate_token", _raise_invalid)

    response = handler.lambda_handler(_authorizer_event("Bearer invalid-token"), None)

    assert response == {
        "isAuthorized": False,
    }


def test_lambda_handler_denies_token_without_sub(monkeypatch):
    monkeypatch.setattr(
        handler,
        "_decode_and_validate_token",
        lambda token: {
            "cognito:groups": ["admin"],
        },
    )

    response = handler.lambda_handler(_authorizer_event("Bearer no-sub-token"), None)

    assert response == {
        "isAuthorized": False,
    }


def test_lambda_handler_reraises_jwks_fetch_error(monkeypatch):
    def _raise_urlerror(_token: str):
        raise URLError("jwks unavailable")

    monkeypatch.setattr(handler, "_decode_and_validate_token", _raise_urlerror)

    with pytest.raises(URLError, match="jwks unavailable"):
        handler.lambda_handler(_authorizer_event("Bearer network-problem"), None)


def test_resolve_bearer_token_accepts_case_insensitive_authorization_header():
    token = handler._resolve_bearer_token(
        {
            "headers": {
                "authorization": "Bearer abc123",
            }
        }
    )

    assert token == "abc123"


def test_claims_include_admin_group_accepts_list_claim():
    assert handler._claims_include_admin_group(["member", "admin"]) is True


def test_claims_include_admin_group_accepts_json_array_string():
    assert handler._claims_include_admin_group('["member", "admin"]') is True


def test_claims_include_admin_group_accepts_exact_string_match():
    assert handler._claims_include_admin_group("admin") is True


def test_claims_include_admin_group_returns_false_for_comma_separated_string():
    assert handler._claims_include_admin_group("member,admin") is False


def test_claims_include_admin_group_raises_for_invalid_json_array_string():
    with pytest.raises(
        InvalidTokenError,
        match="cognito:groups claim JSON string could not be parsed.",
    ):
        handler._claims_include_admin_group("[admin]")


def test_claims_include_admin_group_raises_for_invalid_claim_type():
    with pytest.raises(
        InvalidTokenError,
        match="cognito:groups claim must be a string or list when provided.",
    ):
        handler._claims_include_admin_group({"admin": True})


def test_build_jwks_url_appends_well_known_suffix():
    assert (
        handler._build_jwks_url("https://issuer.example.com/")
        == "https://issuer.example.com/.well-known/jwks.json"
    )


def test_get_required_env_raises_for_blank_value(monkeypatch):
    monkeypatch.setenv("COGNITO_ISSUER", "   ")

    with pytest.raises(
        RuntimeError,
        match="COGNITO_ISSUER environment variable is required.",
    ):
        handler._get_required_env("COGNITO_ISSUER")
