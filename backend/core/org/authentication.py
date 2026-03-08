"""API key authentication for org-level access."""

from __future__ import annotations

from rest_framework.authentication import BaseAuthentication
from rest_framework.request import Request


class APIKeyAuthentication(BaseAuthentication):
    """Authenticate requests using an API key header."""

    def authenticate(self, request: Request) -> tuple | None:  # type: ignore[override]
        return None
