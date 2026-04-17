from __future__ import annotations

from typing import Any, TypedDict


ADMIN_GROUP_NAME = "admin"


class CallerContext(TypedDict):
    # This is the one internal caller shape that business handlers should use
    # after auth normalization. Handlers should not care whether the request
    # originally came from direct test input, a JWT authorizer, or a custom
    # flat authorizer context.
    user_id: str | None
    is_authenticated: bool
    is_admin: bool


def resolve_optional_caller(event: dict[str, Any]) -> CallerContext:
    """Resolve one normalized caller contract from supported event shapes."""
    # Keep the supported edge shapes explicit:
    # 1. synthetic test input under top-level "caller"
    # 2. API Gateway JWT authorizer shape
    # 3. HTTP API simple-response Lambda authorizer shape under "lambda"
    # 4. flat custom-authorizer shape
    # 5. no caller context at all -> anonymous
    if not isinstance(event, dict):
        raise ValueError("Event payload must be a JSON object.")

    synthetic_caller = event.get("caller")
    if synthetic_caller is not None:
        return _normalize_synthetic_caller(synthetic_caller)

    request_context = event.get("requestContext")
    if request_context is None:
        return _anonymous_caller()
    if not isinstance(request_context, dict):
        raise ValueError("requestContext must be an object when provided.")

    authorizer = request_context.get("authorizer")
    if authorizer is None:
        return _anonymous_caller()
    if not isinstance(authorizer, dict):
        raise ValueError("requestContext.authorizer must be an object when provided.")

    jwt_context = authorizer.get("jwt")
    if jwt_context is not None:
        return _normalize_jwt_authorizer_context(jwt_context)

    lambda_context = authorizer.get("lambda")
    if lambda_context is not None:
        return _normalize_lambda_authorizer_context(lambda_context)

    return _normalize_flat_authorizer_context(authorizer)


def require_authenticated_caller(event: dict[str, Any]) -> CallerContext:
    """Resolve caller context and require an authenticated user."""
    # Protected handlers should use this helper instead of re-checking
    # user_id/is_admin manually in each file.
    caller = resolve_optional_caller(event)
    if not caller["is_authenticated"]:
        raise ValueError("Authenticated caller context is required.")
    return caller


def _normalize_synthetic_caller(value: Any) -> CallerContext:
    # Synthetic caller blocks are useful for direct invocation and tests before
    # every real routed path is fully wired. They must still satisfy the same
    # internal caller contract as real authorizer input.
    if not isinstance(value, dict):
        raise ValueError("caller must be an object when provided.")

    is_authenticated = _coerce_bool(
        value.get("is_authenticated", False),
        field_name="caller.is_authenticated",
    )
    is_admin = _coerce_bool(
        value.get("is_admin", False),
        field_name="caller.is_admin",
    )
    user_id = _normalize_optional_string(value.get("user_id"), field_name="caller.user_id")

    return _build_caller_context(
        user_id=user_id,
        is_authenticated=is_authenticated,
        is_admin=is_admin,
        source="caller",
    )


def _normalize_jwt_authorizer_context(value: Any) -> CallerContext:
    # This path matches the HTTP API JWT authorizer shape where claims live
    # under requestContext.authorizer.jwt.claims.
    if not isinstance(value, dict):
        raise ValueError("requestContext.authorizer.jwt must be an object when provided.")

    claims = value.get("claims")
    if claims is None:
        return _anonymous_caller()
    if not isinstance(claims, dict):
        raise ValueError("requestContext.authorizer.jwt.claims must be an object when provided.")

    user_id = _normalize_optional_string(
        claims.get("sub"),
        field_name="requestContext.authorizer.jwt.claims.sub",
    )
    # If there is no usable Cognito "sub", we do not invent identity from
    # other claims. The caller is treated as anonymous instead.
    if not user_id:
        return _anonymous_caller()

    return _build_caller_context(
        user_id=user_id,
        is_authenticated=True,
        is_admin=_claims_include_admin_group(claims.get("cognito:groups")),
        source="requestContext.authorizer.jwt.claims",
    )


def _normalize_flat_authorizer_context(value: dict[str, Any]) -> CallerContext:
    # This path supports the dedicated flat authorizer context shape used by
    # mixed-mode routes such as RSVP.
    if "is_authenticated" not in value:
        if "user_id" in value or "is_admin" in value:
            raise ValueError(
                "requestContext.authorizer.is_authenticated is required when "
                "flat authorizer caller fields are provided."
            )
        return _anonymous_caller()

    is_authenticated = _coerce_bool(
        value.get("is_authenticated"),
        field_name="requestContext.authorizer.is_authenticated",
    )
    is_admin = _coerce_bool(
        value.get("is_admin", False),
        field_name="requestContext.authorizer.is_admin",
    )
    user_id = _normalize_optional_string(
        value.get("user_id"),
        field_name="requestContext.authorizer.user_id",
    )

    return _build_caller_context(
        user_id=user_id,
        is_authenticated=is_authenticated,
        is_admin=is_admin,
        source="requestContext.authorizer",
    )


def _normalize_lambda_authorizer_context(value: Any) -> CallerContext:
    # This path matches the real HTTP API simple-response Lambda authorizer
    # shape observed in AWS, where the custom context is nested under
    # requestContext.authorizer.lambda.
    if not isinstance(value, dict):
        raise ValueError("requestContext.authorizer.lambda must be an object when provided.")

    is_authenticated = _coerce_bool(
        value.get("is_authenticated", False),
        field_name="requestContext.authorizer.lambda.is_authenticated",
    )
    is_admin = _coerce_bool(
        value.get("is_admin", False),
        field_name="requestContext.authorizer.lambda.is_admin",
    )
    user_id = _normalize_optional_string(
        value.get("user_id"),
        field_name="requestContext.authorizer.lambda.user_id",
    )

    return _build_caller_context(
        user_id=user_id,
        is_authenticated=is_authenticated,
        is_admin=is_admin,
        source="requestContext.authorizer.lambda",
    )


def _claims_include_admin_group(raw_value: Any) -> bool:
    # Cognito group claims may arrive as a comma-separated string or a list,
    # depending on how the request context was produced.
    if raw_value is None:
        return False

    if isinstance(raw_value, (list, tuple, set)):
        return any(str(item).strip() == ADMIN_GROUP_NAME for item in raw_value)

    if isinstance(raw_value, str):
        candidate = raw_value.strip()
        if not candidate:
            return False
        # HTTP API JWT claims may arrive as a bracketed string such as
        # "[admin]" instead of a real list. Normalize that shape before
        # applying the usual group-name matching.
        if candidate.startswith("[") and candidate.endswith("]"):
            candidate = candidate[1:-1].strip()
        return any(part.strip() == ADMIN_GROUP_NAME for part in candidate.split(","))

    raise ValueError("requestContext.authorizer.jwt.claims.cognito:groups must be a string or list.")


def _build_caller_context(
    *,
    user_id: str | None,
    is_authenticated: bool,
    is_admin: bool,
    source: str,
) -> CallerContext:
    # Keep the internal contract strict in one place:
    # - authenticated callers must have a user_id
    # - anonymous callers must not have user_id/admin privileges
    if is_authenticated:
        if not user_id:
            raise ValueError(f"{source}.user_id is required when caller is authenticated.")
        return {
            "user_id": user_id,
            "is_authenticated": True,
            "is_admin": is_admin,
        }

    if user_id is not None:
        raise ValueError(f"{source}.user_id must be absent when caller is not authenticated.")
    if is_admin:
        raise ValueError(f"{source}.is_admin must be false when caller is not authenticated.")

    return _anonymous_caller()


def _normalize_optional_string(value: Any, *, field_name: str) -> str | None:
    # Normalize blank strings to None so the rest of the module only has to
    # reason about meaningful string values or the absence of a value.
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string when provided.")

    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _coerce_bool(value: Any, *, field_name: str) -> bool:
    # Keep accepted boolean input intentionally narrow so the auth boundary does
    # not quietly accept surprising values such as 0/1.
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        candidate = value.strip().lower()
        if candidate == "true":
            return True
        if candidate == "false":
            return False

    raise ValueError(f"{field_name} must be a boolean when provided.")


def _anonymous_caller() -> CallerContext:
    # Anonymous is a real internal state, not a missing-key accident.
    return {
        "user_id": None,
        "is_authenticated": False,
        "is_admin": False,
    }
