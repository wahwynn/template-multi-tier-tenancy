"""Consistent error response shape for all API endpoints.

All error responses follow: ``{"error": {"code": "...", "message": "..."}}``.
"""

from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context) -> Response | None:
    """Wrap DRF exceptions in a consistent ``{"error": {...}}`` envelope."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data.get("detail", str(exc))
    if hasattr(detail, "code"):
        code = detail.code
        message = str(detail)
    else:
        code = _status_to_code(response.status_code)
        message = str(detail)

    response.data = {"error": {"code": code, "message": message}}
    return response


def _status_to_code(status_code: int) -> str:
    mapping = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "unprocessable_entity",
        429: "too_many_requests",
        500: "internal_server_error",
    }
    return mapping.get(status_code, "error")
