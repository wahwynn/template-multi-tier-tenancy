"""Tests for authentication backends."""

import hashlib
import secrets
from datetime import timedelta

import pytest
from core.org.authentication import APIKeyAuthentication
from core.org.models import APIKey, OrgUnit, Role
from core.users.authentication import EmailAuthBackend
from core.users.models import User
from django.test import RequestFactory, TestCase
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed


def _make_key() -> tuple[str, str, str]:
    """Return (raw_key, prefix, hashed_key)."""
    raw = secrets.token_hex(32)
    prefix = raw[:8]
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, prefix, hashed


class TestAPIKeyAuthentication(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="alice", email="alice@example.com", password="pass")
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
        request = self.factory.get("/", HTTP_AUTHORIZATION="Bearer invalidkey123456")
        auth = APIKeyAuthentication()
        assert auth.authenticate(request) is None

    def test_expired_api_key_raises_auth_error(self):
        self.api_key.expires_at = timezone.now() - timedelta(hours=1)
        self.api_key.save()
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {self.raw_key}")
        auth = APIKeyAuthentication()
        with pytest.raises(AuthenticationFailed):
            auth.authenticate(request)

    def test_jwt_bearer_token_is_skipped(self):
        request = self.factory.get("/", HTTP_AUTHORIZATION="Bearer eyJhbGciOiJIUzI1NiJ9.fake.jwt")
        auth = APIKeyAuthentication()
        assert auth.authenticate(request) is None


class TestEmailAuthBackend(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bob", email="bob@example.com", password="secret")

    def test_authenticates_by_email(self):
        backend = EmailAuthBackend()
        result = backend.authenticate(None, email="bob@example.com", password="secret")
        assert result == self.user

    def test_wrong_password_returns_none(self):
        backend = EmailAuthBackend()
        result = backend.authenticate(None, email="bob@example.com", password="wrong")
        assert result is None

    def test_unknown_email_returns_none(self):
        backend = EmailAuthBackend()
        result = backend.authenticate(None, email="nobody@example.com", password="secret")
        assert result is None
