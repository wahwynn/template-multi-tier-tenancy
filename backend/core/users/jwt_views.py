"""JWT token views with email login and tenant claim embedding.

Kept separate from authentication.py to avoid a circular import:
authentication.py is loaded at DRF settings init time; importing
simplejwt views here (only loaded by the URL conf) is safe.
"""

from __future__ import annotations

from django.conf import settings as django_settings
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Accept email instead of username and embed tenant slug in the token."""

    username_field = "email"

    @classmethod
    def get_token(cls, user: object) -> object:
        token = super().get_token(user)
        tenant = getattr(django_settings, "_current_tenant", None)
        if tenant:
            token["tenant"] = tenant["slug"]
        return token


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
