"""Tenant resolution middleware.

Resolves the current tenant from the request and sets ``request.tenant``.
Sets the PostgreSQL ``search_path`` to the tenant schema for the duration
of the request.

Resolution order:
1. Path prefix ``/t/<slug>/``
2. ``Host`` header matched against tenant domain list
"""

from __future__ import annotations

from django.conf import settings
from django.db import connection
from django.http import Http404, HttpRequest, HttpResponse

from app.tenants.utils import safe_schema

_safe_schema = safe_schema  # backwards-compatible alias for tests


class TenantMiddleware:
    """Resolve tenant from request and set schema search_path."""

    def __init__(self, get_response) -> None:
        self.get_response = get_response
        self._by_slug: dict[str, dict] = {t["slug"]: t for t in settings.TENANTS}
        self._by_domain: dict[str, dict] = {
            domain: t
            for t in settings.TENANTS
            for domain in t.get("domains", [])
        }

    def __call__(self, request: HttpRequest) -> HttpResponse:
        self._set_tenant(request)
        with connection.cursor() as cursor:
            schema = safe_schema(request.tenant["schema"])
            cursor.execute(f"SET search_path TO {schema}, public")
        return self.get_response(request)

    def _set_tenant(self, request: HttpRequest) -> None:
        tenant = self._resolve(request)
        if tenant is None:
            raise Http404("Tenant not found")
        request.tenant = tenant

    def _resolve(self, request: HttpRequest) -> dict | None:
        # 1. Path prefix: /t/<slug>/...
        path = request.path
        if path.startswith("/t/"):
            parts = path.split("/", 3)
            if len(parts) >= 3 and parts[2]:
                return self._by_slug.get(parts[2])

        # 2. Host header (covers subdomains and custom domains)
        host = request.get_host().split(":")[0]
        return self._by_domain.get(host)
