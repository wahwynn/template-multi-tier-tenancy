"""Authentication backends and classes for user authentication."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.http import HttpRequest
from rest_framework_simplejwt.authentication import JWTAuthentication


class EmailAuthBackend(ModelBackend):
    """Authenticate users by email address instead of username."""

    def authenticate(  # type: ignore[override]
        self,
        request: HttpRequest | None,
        email: str | None = None,
        password: str | None = None,
        **kwargs: object,
    ) -> object:
        User = get_user_model()
        if email is None or password is None:
            return None
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None


class TenantJWTAuthentication(JWTAuthentication):
    """JWT authentication that is tenant-aware."""
