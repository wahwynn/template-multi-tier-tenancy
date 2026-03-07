"""Email-based JWT token views.

Kept separate from authentication.py so that simplejwt view/serializer
imports only happen when the URL conf is loaded, not during DRF settings
initialisation (which would cause a circular import).
"""

from __future__ import annotations

from django.conf import settings as django_settings
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Accept ``email`` + ``password`` and embed the tenant slug in the token."""

    username_field = "email"

    @classmethod
    def get_token(cls, user: object) -> object:
        token = super().get_token(user)
        # Embed slug so tokens cannot be replayed against a different tenant.
        tenant = getattr(django_settings, "_current_tenant", None)
        if tenant:
            token["tenant"] = tenant["slug"]
        return token


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
