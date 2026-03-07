"""API key authentication backend for Django REST Framework.

API keys use the same ``Authorization: Bearer <key>`` header as JWTs.
This backend is checked first; it returns ``None`` for JWT-shaped tokens
(those containing a dot) so that simplejwt can handle them.

Keys are identified by their 8-character prefix, then verified by
comparing the SHA-256 hash of the full key against the stored hash.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

if TYPE_CHECKING:
    from django.http import HttpRequest

    from app.org.models import APIKey


class APIKeyToken:
    """Minimal token-like object carrying the resolved APIKey."""

    def __init__(self, api_key: APIKey) -> None:
        self.api_key = api_key
        self.org_unit = api_key.org_unit
        self.role = api_key.role


class APIKeyAuthentication(BaseAuthentication):
    """Authenticate requests using an API key in the Bearer header."""

    def authenticate_header(self, request: HttpRequest) -> str:
        return 'Bearer realm="api"'

    def authenticate(self, request: HttpRequest) -> tuple | None:
        header: str = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None

        raw_key = header[len("Bearer ") :]

        # JWTs contain dots; raw hex keys do not.
        if "." in raw_key:
            return None

        if len(raw_key) < 8:
            return None

        prefix = raw_key[:8]
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()

        from app.org.models import APIKey  # local import avoids circular

        try:
            key = APIKey.objects.select_related("org_unit", "created_by").get(prefix=prefix, hashed_key=hashed)
        except APIKey.DoesNotExist:
            return None

        if key.expires_at and key.expires_at < timezone.now():
            raise AuthenticationFailed("API key has expired.")

        # Update last_used_at without a full model save.
        APIKey.objects.filter(pk=key.pk).update(last_used_at=timezone.now())

        return key.created_by, APIKeyToken(key)


class EmailAuthBackend:
    """Django auth backend that accepts email instead of username."""

    def authenticate(self, request: HttpRequest | None, username: str | None = None, password: str | None = None, **kwargs: object) -> object | None:
        User = get_user_model()
        email = kwargs.get("email") or username
        if not email or not password:
            return None
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None
        return user if user.check_password(password) and user.is_active else None

    def get_user(self, user_id: int) -> object | None:
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class TenantJWTAuthentication:
    """Wraps simplejwt's JWTAuthentication and enforces the tenant claim.

    Loaded by DRF's DEFAULT_AUTHENTICATION_CLASSES — must not import
    simplejwt views/serializers at module level to avoid a circular import.
    """

    def __init__(self) -> None:
        from rest_framework_simplejwt.authentication import JWTAuthentication

        self._jwt = JWTAuthentication()

    def authenticate(self, request: object) -> tuple | None:
        result = self._jwt.authenticate(request)
        if result is None:
            return None

        user, token = result
        token_tenant = token.get("tenant")
        current_tenant = getattr(request, "tenant", None)
        if token_tenant and current_tenant and token_tenant != current_tenant["slug"]:
            raise AuthenticationFailed("Token is not valid for this tenant.")
        return user, token

    def authenticate_header(self, request: object) -> str:
        return self._jwt.authenticate_header(request)
