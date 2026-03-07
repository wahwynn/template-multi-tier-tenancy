"""Tests for API key authentication."""

import hashlib
import secrets

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from app.org.authentication import APIKeyAuthentication
from app.org.models import APIKey, OrgUnit, Role

User = get_user_model()


def _make_key() -> tuple[str, str, str]:
    """Return (raw_key, prefix, hashed_key)."""
    raw = secrets.token_hex(32)
    prefix = raw[:8]
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, prefix, hashed


class TestAPIKeyAuthentication(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="alice", password="pass")
        self.unit = OrgUnit.objects.create(name="Acme", slug="acme")
        self.raw_key, prefix, hashed = _make_key()
        self.api_key = APIKey.objects.create(
            name="Test Key",
            prefix=prefix,
            hashed_key=hashed,
            org_unit=self.unit,
            role=Role.MEMBER,
            created_by=self.user,
        )

    def test_valid_api_key_authenticates(self):
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {self.raw_key}")
        auth = APIKeyAuthentication()
        result = auth.authenticate(request)
        assert result is not None
        _, token = result
        assert token.org_unit == self.unit

    def test_invalid_api_key_returns_none(self):
        request = self.factory.get("/", HTTP_AUTHORIZATION="Bearer abcd1234invalid")
        auth = APIKeyAuthentication()
        result = auth.authenticate(request)
        assert result is None

    def test_expired_api_key_raises_auth_error(self):
        import pytest
        from rest_framework.exceptions import AuthenticationFailed

        self.api_key.expires_at = timezone.now() - timezone.timedelta(hours=1)
        self.api_key.save()
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {self.raw_key}")
        auth = APIKeyAuthentication()
        with pytest.raises(AuthenticationFailed):
            auth.authenticate(request)

    def test_jwt_bearer_token_is_skipped(self):
        request = self.factory.get("/", HTTP_AUTHORIZATION="Bearer eyJhbGciOiJIUzI1NiJ9.fake.jwt")
        auth = APIKeyAuthentication()
        result = auth.authenticate(request)
        assert result is None

    def test_no_authorization_header_returns_none(self):
        request = self.factory.get("/")
        auth = APIKeyAuthentication()
        result = auth.authenticate(request)
        assert result is None
