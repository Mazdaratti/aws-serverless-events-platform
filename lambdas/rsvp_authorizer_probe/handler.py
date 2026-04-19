from __future__ import annotations

import json
import logging
from typing import Any

from shared.auth import resolve_optional_caller


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # This Lambda exists only as temporary validation infrastructure for the
    # mixed-mode RSVP authorizer rollout. It is intentionally not product
    # behavior. Its job is to expose the actual downstream authorizer shape
    # seen by the integration Lambda in AWS.
    logger.info("rsvp-authorizer-probe invocation started")

    try:
        if not isinstance(event, dict):
            raise ValueError("Event payload must be a JSON object.")

        request_context = event.get("requestContext")
        if request_context is not None and not isinstance(request_context, dict):
            raise ValueError("requestContext must be an object when provided.")

        authorizer_context = None
        if request_context is not None:
            authorizer_context = request_context.get("authorizer")
            if authorizer_context is not None and not isinstance(authorizer_context, dict):
                raise ValueError("requestContext.authorizer must be an object when provided.")

        normalized_caller = resolve_optional_caller(event)

        response_body = {
            "authorizer": authorizer_context,
            "normalized_caller": normalized_caller,
        }

        logger.info("rsvp-authorizer-probe completed")
        return _json_response(status_code=200, body=response_body)
    except ValueError as exc:
        logger.info("rsvp-authorizer-probe validation failed: %s", exc)
        return _json_response(status_code=400, body={"message": str(exc)})
    except Exception:
        logger.exception("rsvp-authorizer-probe failed unexpectedly")
        return _json_response(status_code=500, body={"message": "Internal server error."})


def _json_response(*, status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
