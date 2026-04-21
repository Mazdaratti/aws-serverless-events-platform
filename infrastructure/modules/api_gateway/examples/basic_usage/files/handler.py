"""Tiny example handlers for the API Gateway module basic usage example."""

from __future__ import annotations

import json


def lambda_handler(event, context):
    """Return a minimal HTTP API proxy response for normal route integration."""
    body = {
        "message": "Hello from the API Gateway module example.",
        "routeKey": event.get("routeKey"),
        "rawPath": event.get("rawPath"),
    }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def authorizer_handler(event, context):
    """Return a simple-response allow decision for the request authorizer example."""
    return {
        "isAuthorized": True,
        "context": {
            "user_id": "example-user",
            "is_authenticated": True,
            "is_admin": False,
        },
    }
