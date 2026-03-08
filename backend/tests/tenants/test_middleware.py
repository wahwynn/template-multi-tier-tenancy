"""Tests for TenantMiddleware."""

from unittest.mock import MagicMock, patch

import pytest
from core.tenants.middleware import TenantMiddleware, _safe_schema
from django.http import Http404
from django.test import RequestFactory, override_settings

TENANTS_CONFIG = [
    {"slug": "acme", "schema": "acme", "domains": ["acme.localhost"], "demo": False},
    {"slug": "demo", "schema": "demo", "domains": [], "demo": True},
]


def make_middleware(get_response=None):
    if get_response is None:
        get_response = lambda r: None  # noqa: E731
    return TenantMiddleware(get_response)


@override_settings(TENANTS=TENANTS_CONFIG)
def test_tenant_middleware_resolves_path_prefix():
    factory = RequestFactory()
    request = factory.get("/t/acme/dashboard")
    middleware = make_middleware()
    middleware._set_tenant(request)
    assert request.tenant["slug"] == "acme"


@override_settings(TENANTS=TENANTS_CONFIG, ALLOWED_HOSTS=["acme.localhost"])
def test_tenant_middleware_resolves_domain():
    factory = RequestFactory()
    request = factory.get("/dashboard", SERVER_NAME="acme.localhost")
    middleware = make_middleware()
    middleware._set_tenant(request)
    assert request.tenant["slug"] == "acme"


@override_settings(TENANTS=TENANTS_CONFIG)
def test_tenant_middleware_raises_404_for_unknown_tenant():
    factory = RequestFactory()
    request = factory.get("/t/unknown/dashboard")
    middleware = make_middleware()
    with pytest.raises(Http404):
        middleware._set_tenant(request)


@override_settings(TENANTS=TENANTS_CONFIG)
def test_tenant_middleware_path_prefix_takes_priority_over_domain():
    factory = RequestFactory()
    request = factory.get("/t/demo/dashboard", SERVER_NAME="acme.localhost")
    middleware = make_middleware()
    middleware._set_tenant(request)
    assert request.tenant["slug"] == "demo"


@override_settings(TENANTS=TENANTS_CONFIG, ALLOWED_HOSTS=["unknown.host"])
def test_tenant_middleware_raises_404_for_unknown_domain():
    factory = RequestFactory()
    request = factory.get("/dashboard", SERVER_NAME="unknown.host")
    middleware = make_middleware()
    with pytest.raises(Http404):
        middleware._set_tenant(request)


@override_settings(TENANTS=TENANTS_CONFIG)
def test_tenant_middleware_rewrites_path_prefix():
    factory = RequestFactory()
    request = factory.get("/t/acme/v1/org/units/")
    middleware = make_middleware()
    middleware._set_tenant(request)
    assert request.path == "/v1/org/units/"
    assert request.tenant["slug"] == "acme"


@override_settings(TENANTS=TENANTS_CONFIG)
@patch("core.tenants.middleware.connection")
def test_tenant_middleware_search_path_includes_shared(mock_connection):
    mock_cursor = MagicMock()
    mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=False)
    factory = RequestFactory()
    request = factory.get("/t/acme/dashboard")
    middleware = TenantMiddleware(lambda r: MagicMock())
    middleware(request)
    sql = mock_cursor.execute.call_args[0][0]
    assert "shared" in sql


def test_safe_schema_accepts_valid_name():
    assert _safe_schema("acme") == "acme"
    assert _safe_schema("acme_corp") == "acme_corp"
    assert _safe_schema("tenant123") == "tenant123"


def test_safe_schema_rejects_invalid_name():
    with pytest.raises(ValueError):
        _safe_schema("'; DROP TABLE users; --")
    with pytest.raises(ValueError):
        _safe_schema("123invalid")
    with pytest.raises(ValueError):
        _safe_schema("has space")
