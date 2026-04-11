import pytest

from lambdas.shared.auth import require_authenticated_caller, resolve_optional_caller


def test_resolve_optional_caller_returns_anonymous_when_request_context_is_missing():
    caller = resolve_optional_caller({})

    assert caller == {
        "user_id": None,
        "is_authenticated": False,
        "is_admin": False,
    }


def test_resolve_optional_caller_accepts_synthetic_caller_block():
    caller = resolve_optional_caller(
        {
            "caller": {
                "user_id": "alice",
                "is_authenticated": True,
                "is_admin": False,
            }
        }
    )

    assert caller == {
        "user_id": "alice",
        "is_authenticated": True,
        "is_admin": False,
    }


def test_resolve_optional_caller_accepts_native_jwt_claims_shape():
    caller = resolve_optional_caller(
        {
            "requestContext": {
                "authorizer": {
                    "jwt": {
                        "claims": {
                            "sub": "alice-sub",
                            "cognito:groups": "admin,organizer",
                        }
                    }
                }
            }
        }
    )

    assert caller == {
        "user_id": "alice-sub",
        "is_authenticated": True,
        "is_admin": True,
    }


def test_resolve_optional_caller_returns_anonymous_when_jwt_sub_is_missing():
    caller = resolve_optional_caller(
        {
            "requestContext": {
                "authorizer": {
                    "jwt": {
                        "claims": {
                            "cognito:groups": "admin,organizer",
                        }
                    }
                }
            }
        }
    )

    assert caller == {
        "user_id": None,
        "is_authenticated": False,
        "is_admin": False,
    }


def test_resolve_optional_caller_accepts_custom_authorizer_shape():
    caller = resolve_optional_caller(
        {
            "requestContext": {
                "authorizer": {
                    "user_id": "alice",
                    "is_authenticated": True,
                    "is_admin": False,
                }
            }
        }
    )

    assert caller == {
        "user_id": "alice",
        "is_authenticated": True,
        "is_admin": False,
    }


def test_resolve_optional_caller_returns_anonymous_when_authorizer_is_missing():
    caller = resolve_optional_caller({"requestContext": {}})

    assert caller == {
        "user_id": None,
        "is_authenticated": False,
        "is_admin": False,
    }


def test_require_authenticated_caller_returns_synthetic_caller_when_valid():
    caller = require_authenticated_caller(
        {
            "caller": {
                "user_id": "alice",
                "is_authenticated": True,
                "is_admin": False,
            }
        }
    )

    assert caller == {
        "user_id": "alice",
        "is_authenticated": True,
        "is_admin": False,
    }


def test_require_authenticated_caller_returns_jwt_caller_when_valid():
    caller = require_authenticated_caller(
        {
            "requestContext": {
                "authorizer": {
                    "jwt": {
                        "claims": {
                            "sub": "alice-sub",
                            "cognito:groups": "admin",
                        }
                    }
                }
            }
        }
    )

    assert caller == {
        "user_id": "alice-sub",
        "is_authenticated": True,
        "is_admin": True,
    }


def test_require_authenticated_caller_accepts_bracketed_jwt_groups_string():
    caller = require_authenticated_caller(
        {
            "requestContext": {
                "authorizer": {
                    "jwt": {
                        "claims": {
                            "sub": "alice-sub",
                            "cognito:groups": "[admin]",
                        }
                    }
                }
            }
        }
    )

    assert caller == {
        "user_id": "alice-sub",
        "is_authenticated": True,
        "is_admin": True,
    }


def test_require_authenticated_caller_raises_for_anonymous_event():
    with pytest.raises(ValueError, match="Authenticated caller context is required."):
        require_authenticated_caller({})


def test_resolve_optional_caller_raises_for_invalid_request_context_shape():
    with pytest.raises(ValueError, match="requestContext must be an object when provided."):
        resolve_optional_caller({"requestContext": "not-an-object"})


def test_resolve_optional_caller_raises_when_flat_authorizer_omits_is_authenticated():
    with pytest.raises(
        ValueError,
        match=(
            "requestContext.authorizer.is_authenticated is required when "
            "flat authorizer caller fields are provided."
        ),
    ):
        resolve_optional_caller(
            {
                "requestContext": {
                    "authorizer": {
                        "user_id": "alice",
                        "is_admin": False,
                    }
                }
            }
        )


def test_resolve_optional_caller_raises_for_inconsistent_synthetic_admin_anonymous_state():
    with pytest.raises(ValueError, match=r"caller\.is_admin must be false when caller is not authenticated\."):
        resolve_optional_caller(
            {
                "caller": {
                    "user_id": None,
                    "is_authenticated": False,
                    "is_admin": True,
                }
            }
        )


def test_resolve_optional_caller_raises_for_invalid_jwt_groups_shape():
    with pytest.raises(
        ValueError,
        match=r"requestContext\.authorizer\.jwt\.claims\.cognito:groups must be a string or list\.",
    ):
        resolve_optional_caller(
            {
                "requestContext": {
                    "authorizer": {
                        "jwt": {
                            "claims": {
                                "sub": "alice-sub",
                                "cognito:groups": {"admin": True},
                            }
                        }
                    }
                }
            }
        )
