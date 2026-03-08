"""Authentication backends for the users app.

- EmailAuthBackend: Django auth backend accepting email instead of username.
- TenantJWTAuthentication: DRF backend that wraps simplejwt and validates
  the tenant claim embedded in the token.

Must NOT import simplejwt views/serializers at module level — this file is
loaded by DRF's DEFAULT_AUTHENTICATION_CLASSES during settings init, and doing
so would cause a circular import chain through DRF settings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed

if TYPE_CHECKING:
    from django.http import HttpRequest


class EmailAuthBackend:
    """Django auth backend that accepts email instead of username."""

    def authenticate(
        self,
        request: HttpRequest | None,
        username: str | None = None,
        password: str | None = None,
        **kwargs: object,
    ) -> object | None:
        user_model = get_user_model()
        email = kwargs.get("email") or username
        if not email or not password:
            return None
        try:
            user = user_model.objects.get(email=email)
        except user_model.DoesNotExist:
            return None
        return user if user.check_password(password) and user.is_active else None

    def get_user(self, user_id: object) -> object | None:
        user_model = get_user_model()
        try:
            return user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist:
            return None


class TenantJWTAuthentication:
    """Wraps simplejwt's JWTAuthentication and enforces the tenant claim."""

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
