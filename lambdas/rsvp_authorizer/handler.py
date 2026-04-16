from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib.error import URLError

import jwt
from jwt import InvalidTokenError, PyJWKClient


logger = logging.getLogger()
logger.setLevel(logging.INFO)


DEFAULT_ADMIN_GROUP_NAME = "admin"


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # Keep the authorizer flow small and explicit:
    #
    # 1. validate the top-level event shape
    # 2. resolve the Authorization header
    # 3. if no bearer token is present, allow anonymous access
    # 4. if a bearer token is present, validate it against Cognito
    # 5. project one flat caller context for downstream Lambda use
    logger.info("rsvp-authorizer invocation started")

    try:
        if not isinstance(event, dict):
            raise ValueError("Authorizer event payload must be a JSON object.")

        bearer_token = _resolve_bearer_token(event)
        if bearer_token is None:
            logger.info("rsvp-authorizer allowing anonymous request")
            return _allow_anonymous()

        claims = _decode_and_validate_token(bearer_token)
        caller_context = _build_authenticated_context(claims)

        logger.info(
            "rsvp-authorizer allowing authenticated request for user_id %s",
            caller_context["user_id"],
        )
        return _allow_authenticated(caller_context)
    except InvalidTokenError:
        logger.info("rsvp-authorizer denied invalid token")
        return _deny()
    except ValueError:
        logger.info("rsvp-authorizer denied malformed auth input")
        return _deny()
    except URLError:
        logger.exception("rsvp-authorizer failed to fetch Cognito JWKS")
        raise
    except Exception:
        logger.exception("rsvp-authorizer failed unexpectedly")
        raise


def _resolve_bearer_token(event: dict[str, Any]) -> str | None:
    # HTTP API Lambda authorizers receive raw request headers. This route is
    # mixed-mode, so a missing Authorization header is a valid anonymous case.
    headers = event.get("headers")
    if headers is None:
        return None
    if not isinstance(headers, dict):
        raise ValueError("headers must be an object when provided.")

    raw_header = _get_header_case_insensitive(headers, "authorization")
    if raw_header is None:
        return None
    if not isinstance(raw_header, str):
        raise ValueError("Authorization header must be a string when provided.")

    candidate = raw_header.strip()
    if not candidate:
        raise ValueError("Authorization header must not be blank when provided.")

    scheme, separator, token = candidate.partition(" ")
    if separator == "" or scheme.lower() != "bearer":
        raise ValueError("Authorization header must use Bearer token format.")

    normalized_token = token.strip()
    if not normalized_token:
        raise ValueError("Bearer token must not be empty.")

    return normalized_token


def _get_header_case_insensitive(headers: dict[str, Any], expected_name: str) -> Any:
    for header_name, header_value in headers.items():
        if isinstance(header_name, str) and header_name.lower() == expected_name:
            return header_value
    return None


def _decode_and_validate_token(token: str) -> dict[str, Any]:
    issuer = _get_required_env("COGNITO_ISSUER")
    audience = _get_required_env("COGNITO_APP_CLIENT_ID")
    jwks_client = PyJWKClient(_build_jwks_url(issuer))
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=audience,
        issuer=issuer,
    )
    if not isinstance(claims, dict):
        raise InvalidTokenError("Decoded JWT claims must be an object.")
    return claims


def _build_jwks_url(issuer: str) -> str:
    return f"{issuer.rstrip('/')}/.well-known/jwks.json"


def _build_authenticated_context(claims: dict[str, Any]) -> dict[str, Any]:
    user_id = claims.get("sub")
    if not isinstance(user_id, str) or not user_id.strip():
        raise InvalidTokenError("Verified JWT must include a non-empty sub claim.")

    return {
        "user_id": user_id.strip(),
        "is_authenticated": True,
        "is_admin": _claims_include_admin_group(claims.get("cognito:groups")),
    }


def _claims_include_admin_group(raw_value: Any) -> bool:
    admin_group_name = os.environ.get(
        "COGNITO_ADMIN_GROUP_NAME",
        DEFAULT_ADMIN_GROUP_NAME,
    ).strip()
    if not admin_group_name:
        raise RuntimeError("COGNITO_ADMIN_GROUP_NAME must not be blank when provided.")

    if raw_value is None:
        return False

    if isinstance(raw_value, (list, tuple, set)):
        return any(
            isinstance(item, str) and item.strip() == admin_group_name
            for item in raw_value
        )

    if isinstance(raw_value, str):
        candidate = raw_value.strip()
        if not candidate:
            return False

        if candidate.startswith("[") and candidate.endswith("]"):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError as exc:
                raise InvalidTokenError(
                    "cognito:groups claim JSON string could not be parsed."
                ) from exc

            if not isinstance(parsed, list):
                raise InvalidTokenError(
                    "cognito:groups JSON string must decode to a list."
                )

            return any(
                isinstance(item, str) and item.strip() == admin_group_name
                for item in parsed
            )

        return candidate == admin_group_name

    raise InvalidTokenError("cognito:groups claim must be a string or list when provided.")


def _allow_anonymous() -> dict[str, Any]:
    return {
        "isAuthorized": True,
        "context": {
            "user_id": None,
            "is_authenticated": False,
            "is_admin": False,
        },
    }


def _allow_authenticated(caller_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "isAuthorized": True,
        "context": caller_context,
    }


def _deny() -> dict[str, Any]:
    return {
        "isAuthorized": False,
    }


def _get_required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} environment variable is required.")
    return value
