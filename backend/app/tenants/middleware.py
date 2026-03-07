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

    @property
    def _by_slug(self) -> dict[str, dict]:
        return {t["slug"]: t for t in settings.TENANTS}

    @property
    def _by_domain(self) -> dict[str, dict]:
        return {domain: t for t in settings.TENANTS for domain in t.get("domains", [])}

    def __call__(self, request: HttpRequest) -> HttpResponse:
        self._set_tenant(request)
        schema = safe_schema(request.tenant["schema"])
        with connection.cursor() as cursor:
            cursor.execute(f"SET search_path TO {schema}, public")
        # Expose current tenant on settings so token serializer can embed slug.
        settings._current_tenant = request.tenant
        try:
            return self.get_response(request)
        finally:
            settings._current_tenant = None

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
                tenant = self._by_slug.get(parts[2])
                if tenant is not None:
                    # Rewrite path to strip /t/<slug> prefix
                    new_path = "/" + (parts[3] if len(parts) > 3 else "")
                    request.path_info = new_path
                    request.path = new_path
                return tenant

        # 2. Host header (covers subdomains and custom domains)
        host = request.get_host().split(":")[0]
        return self._by_domain.get(host)
