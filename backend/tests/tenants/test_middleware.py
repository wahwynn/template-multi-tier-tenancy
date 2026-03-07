"""Tests for TenantMiddleware."""

import pytest
from django.http import Http404
from django.test import RequestFactory, override_settings

from app.tenants.middleware import TenantMiddleware

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
