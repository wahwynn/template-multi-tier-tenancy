# Multi-Tenant Scaffold Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Scaffold a full-stack multi-tenant application with three-tier PostgreSQL schema isolation, unlimited-depth org hierarchy, flexible role-based membership, email-based JWT auth with tenant claims, and API key authentication.

**Architecture:** Django backend with custom tenant middleware resolving tenants from env config (12-factor). Three-tier schema layout: `public` (PostgreSQL system only, locked), `shared` (Django auth/contenttypes), `{tenant}` (all app tables). The `shared` schema is the default destination for non-tenant operations. Each tenant schema has its own `django_migrations` table. Next.js frontend with JWT auth and `next-intl` i18n scaffolding.

**Tech Stack:** Django 6, DRF, djangorestframework-simplejwt, django-cors-headers, dj-database-url, PostgreSQL 16, Redis 7, Next.js 15 (App Router), TypeScript, next-intl, Docker Compose, pytest, Vitest, uv

**Design doc:** `docs/plans/2026-03-07-multi-tenant-scaffold-design.md`

---

## Prerequisites

- Docker Desktop running
- `uv` installed (`brew install uv`)
- Node.js 22+ installed

---

## Task 1: Update PROJECT.md and create directory structure

**Files:**
- Modify: `PROJECT.md`

**Step 1: Update PROJECT.md with stack decisions**

Replace the contents of `PROJECT.md`:

```markdown
# Project Metadata

- **Project type**: full-stack
- **Backend framework**: Django 6 + Django REST Framework
- **Frontend framework**: Next.js 15 (App Router) + TypeScript
- **Database**: PostgreSQL 16 (three-tier schema isolation: public / shared / tenant)
- **Cache**: Redis 7

## Project Structure

\`\`\`
frontend/          ← Next.js frontend
backend/           ← Django backend
docker-compose.yml ← Local development orchestration
\`\`\`

See `docs/plans/2026-03-07-multi-tenant-scaffold-design.md` for architecture decisions.
```

**Step 2: Create top-level directories**

```bash
mkdir -p backend frontend backend/docker
```

**Step 3: Commit**

```bash
git add PROJECT.md
git commit -m "chore: establish project structure and update PROJECT.md"
```

---

## Task 2: Docker Compose, environment config, and PostgreSQL init

**Files:**
- Modify: `docker-compose.yml`
- Create: `.env.example`
- Create: `backend/docker/init_db.sql`

**Context:** The PostgreSQL `init_db.sql` script runs once at container creation time (as the postgres superuser via `/docker-entrypoint-initdb.d/`). It creates the `shared` schema, grants access to the app user, sets the role-level default `search_path` so that plain `manage.py migrate` writes to `shared` instead of `public`, and locks `public` against app writes.

**Step 1: Create backend/docker/init_db.sql**

```sql
-- Shared schema for non-tenant Django operations (auth, contenttypes, django_migrations).
-- Runs once at database creation time as the postgres superuser.

CREATE SCHEMA IF NOT EXISTS shared;
GRANT ALL ON SCHEMA shared TO app;

-- Set the default search_path for the app role so that plain
-- manage.py migrate writes to shared instead of public.
ALTER ROLE app SET search_path TO shared, public;

-- Lock public: prevent the app user from creating tables there.
-- (PostgreSQL 15+ revokes CREATE on public from PUBLIC by default;
-- this is explicit for clarity and older versions.)
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM app;
```

**Step 2: Write docker-compose.yml**

Replace the existing `docker-compose.yml` with:

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - TENANTS=${TENANTS}
      - DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
      - JWT_ACCESS_TOKEN_EXPIRY=${JWT_ACCESS_TOKEN_EXPIRY:-3600}
      - JWT_REFRESH_TOKEN_EXPIRY=${JWT_REFRESH_TOKEN_EXPIRY:-86400}
      - DEBUG=${DEBUG:-true}
      - DJANGO_ALLOWED_HOSTS=${DJANGO_ALLOWED_HOSTS:-localhost,127.0.0.1}
      - CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS:-}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uv run manage.py runserver 0.0.0.0:8000

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    environment:
      - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-http://localhost:8000}
      - NEXT_PUBLIC_TENANTS=${TENANTS}
    depends_on:
      - backend
    command: npm run dev

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/docker/init_db.sql:/docker-entrypoint-initdb.d/init_db.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

**Step 3: Write .env.example**

```bash
# Tenant configuration (JSON array)
# Each tenant: slug (URL identifier), schema (PostgreSQL schema name),
# domains (list of hostnames for production), demo (optional bool)
TENANTS='[{"slug":"acme","schema":"acme","domains":["acme.localhost"],"demo":false},{"slug":"demo","schema":"demo","domains":[],"demo":true}]'

# Database
DATABASE_URL=postgres://app:app@localhost:5432/app

# Redis
REDIS_URL=redis://localhost:6379/0

# Auth
DJANGO_SECRET_KEY=change-me-in-production-use-a-long-random-string
JWT_ACCESS_TOKEN_EXPIRY=3600
JWT_REFRESH_TOKEN_EXPIRY=86400

# Django
DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# CORS — leave empty in dev (falls back to CORS_ALLOW_ALL_ORIGINS=DEBUG)
CORS_ALLOWED_ORIGINS=

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Step 4: Copy .env.example to .env**

```bash
cp .env.example .env
```

**Step 5: Commit**

```bash
git add docker-compose.yml .env.example backend/docker/init_db.sql
git commit -m "chore: add Docker Compose, env config, and PostgreSQL shared schema init"
```

---

## Task 3: Django project setup

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/manage.py`
- Create: `backend/config/`
- Create: `backend/Dockerfile`

**Step 1: Initialise Django project with uv**

```bash
cd backend
uv init --no-readme --python 3.14
uv add django djangorestframework djangorestframework-simplejwt django-cors-headers dj-database-url psycopg[binary] redis django-redis
uv add --dev pytest pytest-django ruff
```

**Step 2: Create Django project**

```bash
uv run django-admin startproject config .
```

This creates `manage.py` and `config/` (with `settings.py`, `urls.py`, `wsgi.py`).

**Step 3: Replace config/settings.py**

```python
"""Django settings for multi-tenant scaffold."""

from __future__ import annotations

import json
import os
from datetime import timedelta
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Security ---
SECRET_KEY: str = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"
ALLOWED_HOSTS: list[str] = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# --- Tenants (12-factor: loaded from env, never from DB) ---
TENANTS: list[dict] = json.loads(os.environ.get("TENANTS", "[]"))

# --- Installed apps ---
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "app.tenants",
    "app.org",
]

# SessionMiddleware and AuthenticationMiddleware intentionally omitted.
# This is a stateless JWT/API-key API — no server-side sessions or CSRF.
# CorsMiddleware must come before TenantMiddleware so preflight OPTIONS
# requests are handled before tenant resolution runs.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "app.tenants.middleware.TenantMiddleware",
    "django.middleware.common.CommonMiddleware",
]

# --- CORS ---
# In development allow all origins when DEBUG is on.
# In production set CORS_ALLOWED_ORIGINS to the actual frontend domain(s).
_cors_origins_env = os.environ.get("CORS_ALLOWED_ORIGINS", "")
CORS_ALLOWED_ORIGINS: list[str] = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
if not CORS_ALLOWED_ORIGINS:
    CORS_ALLOW_ALL_ORIGINS: bool = DEBUG

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database ---
DATABASES = {"default": dj_database_url.parse(os.environ.get("DATABASE_URL", "postgres://app:app@localhost:5432/app"))}

# --- Cache ---
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

# --- Auth ---
# Custom User model with UUID primary key lives in app_org.
AUTH_USER_MODEL = "app_org.User"
AUTHENTICATION_BACKENDS = ["app.org.authentication.EmailAuthBackend"]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "app.org.authentication.APIKeyAuthentication",
        "app.org.authentication.TenantJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.CursorPagination",
    "PAGE_SIZE": 50,
    "EXCEPTION_HANDLER": "app.tenants.exceptions.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(seconds=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRY", "3600"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(seconds=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRY", "86400"))),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en-us"
USE_TZ = True
```

**Step 4: Write config/urls.py**

```python
from django.urls import include, path
from app.org.jwt_views import EmailTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("v1/auth/token/", EmailTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("v1/org/", include("app.org.urls")),
]
```

**Step 5: Write backend/Dockerfile**

```dockerfile
FROM python:3.14-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen

COPY . .

EXPOSE 8000
```

**Step 6: Write backend/pytest.ini**

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

**Step 7: Create app package directories**

```bash
mkdir -p app/tenants/management/commands app/org
touch app/__init__.py app/tenants/__init__.py app/tenants/management/__init__.py app/tenants/management/commands/__init__.py app/org/__init__.py
mkdir -p tests/tenants tests/org
touch tests/__init__.py tests/tenants/__init__.py tests/org/__init__.py
```

**Step 8: Commit**

```bash
git add backend/
git commit -m "chore: initialise Django project with uv and core settings"
```

---

## Task 4: Tenant utilities

**Files:**
- Create: `backend/app/tenants/utils.py`
- Test inline in task 5 middleware tests (safe_schema is simple enough to test via middleware)

**Context:** `safe_schema` validates that a schema name is safe to interpolate into a SQL identifier position. It must be called before any `SET search_path` or `CREATE SCHEMA` SQL. All management commands and middleware must use it.

**Step 1: Create backend/app/tenants/utils.py**

```python
"""Shared utilities for tenant management."""

from __future__ import annotations

import re

_VALID_SCHEMA_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def safe_schema(schema: str) -> str:
    """Validate schema is a safe PostgreSQL identifier before use in SQL.

    Raises ValueError if the name contains characters that are unsafe
    to interpolate into a SQL identifier position.
    """
    if not _VALID_SCHEMA_RE.match(schema):
        raise ValueError(f"Invalid schema name: {schema!r}")
    return schema
```

**Step 2: Commit**

```bash
git add app/tenants/utils.py
git commit -m "feat: add safe_schema validator utility"
```

---

## Task 5: Tenant middleware

**Files:**
- Create: `backend/app/tenants/middleware.py`
- Create: `backend/tests/tenants/test_middleware.py`

**Context:** Middleware responsibilities:
1. Resolve tenant from path prefix `/t/<slug>/` (dev) or `Host` header (prod)
2. Strip `/t/<slug>` prefix from `request.path` so URL routing is unaffected
3. Set `search_path = {schema}, shared, public` for the duration of the request
4. Expose `request.tenant` and `settings._current_tenant` (used by JWT serializer)
5. Raise `Http404` for unknown tenants

**Step 1: Write the failing tests**

Create `backend/tests/tenants/test_middleware.py`:

```python
"""Tests for TenantMiddleware."""

from unittest.mock import MagicMock, patch

import pytest
from django.http import Http404
from django.test import RequestFactory, override_settings

from app.tenants.middleware import TenantMiddleware, _safe_schema

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
@patch("app.tenants.middleware.connection")
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
```

**Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/tenants/test_middleware.py -v
```

Expected: `FAILED` — `app.tenants.middleware` does not exist yet.

**Step 3: Implement TenantMiddleware**

Create `backend/app/tenants/middleware.py`:

```python
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
            cursor.execute(f"SET search_path TO {schema}, shared, public")
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
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/tenants/test_middleware.py -v
```

Expected: all PASSED.

**Step 5: Commit**

```bash
git add app/tenants/middleware.py tests/tenants/test_middleware.py
git commit -m "feat: add TenantMiddleware with path-prefix resolution, path rewriting, and shared schema"
```

---

## Task 6: Custom exception handler

**Files:**
- Create: `backend/app/tenants/exceptions.py`
- Create: `backend/tests/tenants/test_exceptions.py`

**Step 1: Write the failing test**

```python
"""Tests for custom exception handler."""

from django.core.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.test import APIRequestFactory

from app.tenants.exceptions import custom_exception_handler


def test_custom_exception_handler_formats_drf_exception():
    factory = APIRequestFactory()
    request = factory.get("/")
    exc = NotFound("resource not found")
    response = custom_exception_handler(exc, {"request": request})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data == {"error": {"code": "not_found", "message": "resource not found"}}


def test_custom_exception_handler_returns_none_for_unknown():
    response = custom_exception_handler(ValueError("oops"), {})
    assert response is None
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/tenants/test_exceptions.py -v
```

**Step 3: Implement exception handler**

Create `backend/app/tenants/exceptions.py`:

```python
"""Consistent error response shape for all API endpoints.

All error responses follow: ``{"error": {"code": "...", "message": "..."}}``.
"""

from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc: Exception, context: dict) -> Response | None:
    """Wrap DRF exceptions in a consistent ``{"error": {...}}`` envelope."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data.get("detail", str(exc))
    if hasattr(detail, "code"):
        code = detail.code
        message = str(detail)
    else:
        code = _status_to_code(response.status_code)
        message = str(detail)

    response.data = {"error": {"code": code, "message": message}}
    return response


def _status_to_code(status_code: int) -> str:
    mapping = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        429: "too_many_requests",
        500: "server_error",
    }
    return mapping.get(status_code, "error")
```

**Step 4: Run tests**

```bash
uv run pytest tests/tenants/test_exceptions.py -v
```

**Step 5: Commit**

```bash
git add app/tenants/exceptions.py tests/tenants/test_exceptions.py
git commit -m "feat: add consistent API error response format"
```

---

## Task 7: Management commands — migrate_shared, create_tenant, migrate_tenants

**Files:**
- Create: `backend/app/tenants/management/commands/migrate_shared.py`
- Create: `backend/app/tenants/management/commands/create_tenant.py`
- Create: `backend/app/tenants/management/commands/migrate_tenants.py`
- Create: `backend/tests/tenants/test_management_commands.py`

**Context:** Three-tier database setup order:
1. `migrate_shared` — runs Django migrations into the `shared` schema (auth, contenttypes). Run once on a fresh database before provisioning any tenants.
2. `create_tenant <slug>` — creates the tenant's PostgreSQL schema and runs `migrate_tenants` for it.
3. `migrate_tenants [--schema <name>]` — fans out `migrate` across all (or one) tenant schemas.

`migrate_tenants` uses the connection options approach (not a cursor-level `SET`) because Django's `migrate` command may internally reconnect, resetting session-level search_path. Baking it into `connection.settings_dict["OPTIONS"]["options"]` ensures it persists.

**Step 1: Write the failing tests**

Create `backend/tests/tenants/test_management_commands.py`:

```python
"""Tests for tenant management commands."""

from unittest.mock import MagicMock, patch

import pytest
from django.core.management.base import CommandError
from django.test import override_settings

from app.tenants.management.commands.create_tenant import Command as CreateTenantCommand
from app.tenants.management.commands.migrate_shared import Command as MigrateSharedCommand
from app.tenants.management.commands.migrate_tenants import Command as MigrateTenantsCommand

TENANTS_CONFIG = [
    {"slug": "acme", "schema": "acme", "domains": ["acme.localhost"]},
    {"slug": "demo", "schema": "demo", "domains": []},
]


@patch("app.tenants.management.commands.migrate_shared.call_command")
@patch("app.tenants.management.commands.migrate_shared.connection")
def test_migrate_shared_creates_schema_and_runs_migrate(mock_connection, mock_call_command):
    mock_cursor = MagicMock()
    mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_connection.settings_dict = {"OPTIONS": {}}

    cmd = MigrateSharedCommand()
    cmd.handle(verbosity=1)

    mock_cursor.execute.assert_called_once_with("CREATE SCHEMA IF NOT EXISTS shared")
    mock_call_command.assert_called_once_with("migrate", verbosity=1)


@override_settings(TENANTS=TENANTS_CONFIG)
@patch("app.tenants.management.commands.create_tenant.call_command")
@patch("app.tenants.management.commands.create_tenant.connection")
def test_create_tenant_creates_schema_and_runs_migrations(mock_connection, mock_call_command):
    mock_cursor = MagicMock()
    mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=False)

    cmd = CreateTenantCommand()
    cmd.handle(slug="acme", verbosity=1)

    mock_cursor.execute.assert_called_once_with("CREATE SCHEMA IF NOT EXISTS acme")
    mock_call_command.assert_called_once_with("migrate_tenants", "--schema", "acme", verbosity=1)


@override_settings(TENANTS=TENANTS_CONFIG)
def test_create_tenant_raises_error_for_unknown_slug():
    cmd = CreateTenantCommand()
    with pytest.raises(CommandError):
        cmd.handle(slug="unknown", verbosity=1)


@override_settings(TENANTS=TENANTS_CONFIG)
@patch("app.tenants.management.commands.migrate_tenants.call_command")
@patch("app.tenants.management.commands.migrate_tenants.connection")
def test_migrate_tenants_runs_migrate_for_all_tenants(mock_connection, mock_call_command):
    mock_connection.settings_dict = {"OPTIONS": {}}

    cmd = MigrateTenantsCommand()
    cmd.handle(schema=None, verbosity=1)

    assert mock_call_command.call_count == 2
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/tenants/test_management_commands.py -v
```

Expected: `FAILED` — modules do not exist yet.

**Step 3: Implement migrate_shared**

Create `backend/app/tenants/management/commands/migrate_shared.py`:

```python
"""Management command: migrate_shared.

Runs Django migrations for shared (non-tenant) apps into the 'shared'
PostgreSQL schema. Must be run once before create_tenant on a fresh database.

Usage:
    uv run manage.py migrate_shared
"""

from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Run Django migrations for shared apps into the 'shared' schema."

    def handle(self, *args: object, **options: object) -> None:
        self.stdout.write("Ensuring 'shared' schema exists...")
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS shared")

        self.stdout.write("Migrating shared schema...")
        original_options = connection.settings_dict.get("OPTIONS", {}).copy()
        try:
            connection.settings_dict.setdefault("OPTIONS", {})
            connection.settings_dict["OPTIONS"]["options"] = "-c search_path=shared,public"
            connection.close()
            call_command("migrate", verbosity=options["verbosity"])
            self.stdout.write(self.style.SUCCESS("  'shared' OK"))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"  'shared' FAILED: {exc}"))
            raise
        finally:
            connection.settings_dict["OPTIONS"] = original_options
            connection.close()
```

**Step 4: Implement create_tenant**

Create `backend/app/tenants/management/commands/create_tenant.py`:

```python
"""Management command: create_tenant.

Usage:
    uv run manage.py create_tenant <slug>

Creates the PostgreSQL schema for the given tenant slug and runs
migrations into it. Run migrate_shared first on a fresh database.
"""

from __future__ import annotations

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from app.tenants.utils import safe_schema


class Command(BaseCommand):
    help = "Create a PostgreSQL schema for a tenant and run migrations."

    def add_arguments(self, parser) -> None:
        parser.add_argument("slug", type=str, help="Tenant slug (must exist in TENANTS config)")

    def handle(self, *args: object, **options: object) -> None:
        slug: str = options["slug"]
        tenant = next((t for t in settings.TENANTS if t["slug"] == slug), None)
        if tenant is None:
            raise CommandError(f"Tenant '{slug}' not found in TENANTS config.")

        schema = safe_schema(tenant["schema"])
        self.stdout.write(f"Creating schema '{schema}'...")
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

        self.stdout.write(f"Running migrations for schema '{schema}'...")
        call_command("migrate_tenants", "--schema", schema, verbosity=options["verbosity"])
        self.stdout.write(self.style.SUCCESS(f"Tenant '{slug}' ready."))
```

**Step 5: Implement migrate_tenants**

Create `backend/app/tenants/management/commands/migrate_tenants.py`:

```python
"""Management command: migrate_tenants.

Usage:
    uv run manage.py migrate_tenants              # all tenants
    uv run manage.py migrate_tenants --schema acme  # one tenant

Fans out Django migrate across all (or one) tenant schemas.
Safe to re-run: each schema tracks its own django_migrations state.
"""

from __future__ import annotations

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

from app.tenants.utils import safe_schema


class Command(BaseCommand):
    help = "Run Django migrations across all (or one) tenant schemas."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--schema",
            type=str,
            default=None,
            help="Limit to a single schema. Defaults to all tenants.",
        )

    def handle(self, *args: object, **options: object) -> None:
        target_schema: str | None = options.get("schema")

        tenants = settings.TENANTS
        if target_schema:
            tenants = [t for t in tenants if t["schema"] == target_schema]

        for tenant in tenants:
            schema = safe_schema(tenant["schema"])
            self.stdout.write(f"Migrating schema '{schema}'...")
            # Bake search_path into connection options so it persists across
            # any reconnect that Django's migrate command may trigger internally.
            original_options = connection.settings_dict.get("OPTIONS", {}).copy()
            try:
                connection.settings_dict.setdefault("OPTIONS", {})
                connection.settings_dict["OPTIONS"]["options"] = f"-c search_path={schema},shared,public"
                connection.close()
                call_command("migrate", verbosity=options["verbosity"])
                self.stdout.write(self.style.SUCCESS(f"  '{schema}' OK"))
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"  '{schema}' FAILED: {exc}"))
                raise
            finally:
                connection.settings_dict["OPTIONS"] = original_options
                connection.close()
```

**Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/tenants/test_management_commands.py -v
```

Expected: all PASSED.

**Step 7: Commit**

```bash
git add app/tenants/management/ tests/tenants/test_management_commands.py
git commit -m "feat: add migrate_shared, create_tenant, and migrate_tenants management commands"
```

---

## Task 8: Models — User, OrgUnit, Membership, APIKey

**Files:**
- Create: `backend/app/org/models.py`
- Create: `backend/app/org/apps.py`
- Create: `backend/app/org/migrations/0001_initial.py`
- Create: `backend/tests/org/test_org_unit.py`

**Context:** All models live in the `app_org` app (label set in Meta). The custom `User` model with a UUID primary key is defined here (not in `django.contrib.auth`) so that `AUTH_USER_MODEL = "app_org.User"` resolves correctly. The initial migration includes the User model inline — no `swappable_dependency` — which avoids a circular migration dependency. FKs to User use `"app_org.user"` (hardcoded) not `settings.AUTH_USER_MODEL`.

**Step 1: Write the failing tests**

Create `backend/tests/org/test_org_unit.py`:

```python
"""Tests for OrgUnit model."""

import pytest
from django.test import TestCase

from app.org.models import IsolationPolicy, OrgUnit


class TestOrgUnitCreation(TestCase):
    def test_create_root_org_unit(self):
        unit = OrgUnit.objects.create(name="Acme Corp", slug="acme-corp", node_type="org")
        assert unit.parent is None
        assert unit.isolation_policy == IsolationPolicy.OPEN

    def test_create_child_org_unit(self):
        parent = OrgUnit.objects.create(name="Acme Corp", slug="acme", node_type="org")
        child = OrgUnit.objects.create(name="Engineering", slug="engineering", node_type="department", parent=parent)
        assert child.parent == parent

    def test_isolation_policy_choices(self):
        assert set(IsolationPolicy.values) == {"open", "isolated", "inherit_only", "visible_only"}


class TestOrgUnitAncestors(TestCase):
    def setUp(self):
        self.corp = OrgUnit.objects.create(name="Corp", slug="corp", node_type="org")
        self.dept = OrgUnit.objects.create(name="Dept", slug="dept", node_type="department", parent=self.corp)
        self.team = OrgUnit.objects.create(name="Team", slug="team", node_type="team", parent=self.dept)

    def test_get_ancestors(self):
        ancestors = self.team.get_ancestors()
        assert list(ancestors) == [self.dept, self.corp]

    def test_get_descendants(self):
        descendants = self.corp.get_descendants()
        pks = {u.pk for u in descendants}
        assert pks == {self.dept.pk, self.team.pk}

    def test_root_node_has_no_ancestors(self):
        assert list(self.corp.get_ancestors()) == []
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/org/test_org_unit.py -v
```

**Step 3: Create app/org/apps.py**

```python
from django.apps import AppConfig


class OrgConfig(AppConfig):
    name = "app.org"
    label = "app_org"
```

Add to `app/org/__init__.py`:

```python
default_app_config = "app.org.apps.OrgConfig"
```

**Step 4: Implement models**

Create `backend/app/org/models.py`:

```python
"""Org hierarchy models.

OrgUnit is a self-referential tree node representing any level of
organisational structure (org, department, team, franchise, etc.).

Isolation policy controls data visibility across parent/child boundaries:
- open:         parent sees in, child sees parent (default)
- isolated:     neither direction crosses the boundary
- inherit_only: child sees parent, parent cannot see in
- visible_only: parent sees in, child cannot see parent
"""

from __future__ import annotations

import uuid
from typing import ClassVar

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with UUID primary key."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        app_label = "app_org"


class IsolationPolicy(models.TextChoices):
    OPEN = "open", "Open"
    ISOLATED = "isolated", "Isolated"
    INHERIT_ONLY = "inherit_only", "Inherit Only"
    VISIBLE_ONLY = "visible_only", "Visible Only"


class Role(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    MEMBER = "member", "Member"
    VIEWER = "viewer", "Viewer"


class OrgUnit(models.Model):
    """A node in the organisational hierarchy."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    node_type = models.CharField(max_length=100, default="org")
    isolation_policy = models.CharField(
        max_length=20,
        choices=IsolationPolicy.choices,
        default=IsolationPolicy.OPEN,
    )

    class Meta:
        app_label = "app_org"

    def __str__(self) -> str:
        return self.name

    def get_ancestors(self) -> list[OrgUnit]:
        """Return list of ancestors from immediate parent to root."""
        ancestors: list[OrgUnit] = []
        current = self.parent
        while current is not None:
            ancestors.append(current)
            current = current.parent
        return ancestors

    def get_descendants(self) -> list[OrgUnit]:
        """Return all descendant nodes via recursive CTE."""
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH RECURSIVE descendants AS (
                    SELECT id FROM app_org_orgunit WHERE parent_id = %s
                    UNION ALL
                    SELECT o.id FROM app_org_orgunit o
                    INNER JOIN descendants d ON o.parent_id = d.id
                )
                SELECT id FROM descendants
                """,
                [str(self.pk)],
            )
            ids = [row[0] for row in cursor.fetchall()]
        return list(OrgUnit.objects.filter(pk__in=ids))


class Membership(models.Model):
    """Explicit membership of a User in an OrgUnit with a role."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    org_unit = models.ForeignKey(
        OrgUnit,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        app_label = "app_org"
        constraints: ClassVar = [models.UniqueConstraint(fields=["user", "org_unit"], name="unique_user_org_unit")]

    def __str__(self) -> str:
        return f"{self.user} in {self.org_unit} ({self.role})"


class APIKey(models.Model):
    """An API key scoped to an OrgUnit for external integrations."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    prefix = models.CharField(max_length=8, db_index=True)
    hashed_key = models.CharField(max_length=64)
    org_unit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE, related_name="api_keys")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_api_keys",
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "app_org"
        constraints: ClassVar = [models.UniqueConstraint(fields=["prefix", "hashed_key"], name="unique_api_key")]

    def __str__(self) -> str:
        return f"{self.name} ({self.prefix}...)"
```

**Step 5: Create the initial migration**

Create `backend/app/org/migrations/__init__.py` (empty), then create `backend/app/org/migrations/0001_initial.py`:

```python
import uuid

import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    # Depend on auth (for auth.Group and auth.Permission M2M), NOT on
    # swappable_dependency — that would create a circular dependency since
    # User is defined in this same app.
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, verbose_name="superuser status")),
                (
                    "username",
                    models.CharField(
                        error_messages={"unique": "A user with that username already exists."},
                        max_length=150,
                        unique=True,
                        validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
                        verbose_name="username",
                    ),
                ),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="email address")),
                ("is_staff", models.BooleanField(default=False, verbose_name="staff status")),
                ("is_active", models.BooleanField(default=True, verbose_name="active")),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True, related_name="user_set", related_query_name="user",
                        to="auth.group", verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True, related_name="user_set", related_query_name="user",
                        to="auth.permission", verbose_name="user permissions",
                    ),
                ),
            ],
            options={"app_label": "app_org"},
            managers=[("objects", django.contrib.auth.models.UserManager())],
        ),
        migrations.CreateModel(
            name="OrgUnit",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=100)),
                ("node_type", models.CharField(default="org", max_length=100)),
                (
                    "isolation_policy",
                    models.CharField(
                        choices=[("open", "Open"), ("isolated", "Isolated"), ("inherit_only", "Inherit Only"), ("visible_only", "Visible Only")],
                        default="open", max_length=20,
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                        related_name="children", to="app_org.orgunit",
                    ),
                ),
            ],
            options={"app_label": "app_org"},
        ),
        migrations.CreateModel(
            name="Membership",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "role",
                    models.CharField(
                        choices=[("owner", "Owner"), ("admin", "Admin"), ("member", "Member"), ("viewer", "Viewer")],
                        default="member", max_length=20,
                    ),
                ),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="app_org.user")),
                ("org_unit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="app_org.orgunit")),
            ],
            options={
                "app_label": "app_org",
                "constraints": [models.UniqueConstraint(fields=("user", "org_unit"), name="unique_user_org_unit")],
            },
        ),
        migrations.CreateModel(
            name="APIKey",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("prefix", models.CharField(db_index=True, max_length=8)),
                ("hashed_key", models.CharField(max_length=64)),
                (
                    "role",
                    models.CharField(
                        choices=[("owner", "Owner"), ("admin", "Admin"), ("member", "Member"), ("viewer", "Viewer")],
                        default="member", max_length=20,
                    ),
                ),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_api_keys", to="app_org.user")),
                ("org_unit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="api_keys", to="app_org.orgunit")),
            ],
            options={
                "app_label": "app_org",
                "constraints": [models.UniqueConstraint(fields=("prefix", "hashed_key"), name="unique_api_key")],
            },
        ),
    ]
```

**Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/org/test_org_unit.py -v
```

Expected: all PASSED.

**Step 7: Commit**

```bash
git add app/org/ tests/org/test_org_unit.py
git commit -m "feat: add User (UUID PK), OrgUnit, Membership, and APIKey models"
```

---

## Task 9: Authentication — email auth, API keys, tenant JWT

**Files:**
- Create: `backend/app/org/authentication.py`
- Create: `backend/app/org/jwt_views.py`
- Create: `backend/tests/org/test_authentication.py`

**Context:** Three authentication paths:
1. **API key** — `Authorization: Bearer <hex-key>` (no dots). Hashed and looked up against `APIKey` table.
2. **Email JWT** — `Authorization: Bearer <jwt>` (contains dots). Validated by `TenantJWTAuthentication`, which wraps simplejwt and also validates the `tenant` claim in the token against the current request tenant.
3. **Login** — `POST /v1/auth/token/` with `{ "email": "...", "password": "..." }`. `EmailAuthBackend` authenticates by email instead of username. `EmailTokenObtainPairSerializer` embeds the tenant slug as a `tenant` claim in the JWT.

`jwt_views.py` is a separate file (not imported by `authentication.py`) to avoid a circular import: `authentication.py` is loaded by DRF at startup via `DEFAULT_AUTHENTICATION_CLASSES`; importing simplejwt views at that point triggers a circular import chain through DRF settings.

**Step 1: Write the failing tests**

Create `backend/tests/org/test_authentication.py`:

```python
"""Tests for authentication backends."""

import hashlib
import secrets

import pytest
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed

from app.org.authentication import APIKeyAuthentication, EmailAuthBackend
from app.org.models import APIKey, OrgUnit, Role, User


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
            name="Test Key", prefix=prefix, hashed_key=hashed,
            org_unit=self.unit, role=Role.MEMBER, created_by=self.user,
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
        self.api_key.expires_at = timezone.now() - timezone.timedelta(hours=1)
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
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/org/test_authentication.py -v
```

**Step 3: Implement authentication.py**

Create `backend/app/org/authentication.py`:

```python
"""Authentication backends for Django and DRF.

Three classes:
- APIKeyAuthentication: DRF backend for Bearer <hex-key> tokens
- EmailAuthBackend: Django auth backend accepting email instead of username
- TenantJWTAuthentication: wraps simplejwt and validates the tenant claim

Imports are structured carefully to avoid circular imports at module load time:
simplejwt views/serializers must NOT be imported at module level here, because
this file is loaded by DRF's DEFAULT_AUTHENTICATION_CLASSES during settings init.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

if TYPE_CHECKING:
    from django.http import HttpRequest

    from app.org.models import APIKey


class APIKeyToken:
    """Minimal token-like object carrying the resolved APIKey."""

    def __init__(self, api_key: APIKey) -> None:
        self.api_key = api_key
        self.org_unit = api_key.org_unit
        self.role = api_key.role


class APIKeyAuthentication(BaseAuthentication):
    """Authenticate requests using an API key in the Bearer header."""

    def authenticate_header(self, request: HttpRequest) -> str:
        return 'Bearer realm="api"'

    def authenticate(self, request: HttpRequest) -> tuple | None:
        header: str = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None

        raw_key = header[len("Bearer "):]

        # JWTs contain dots; raw hex keys do not.
        if "." in raw_key:
            return None

        if len(raw_key) < 8:
            return None

        prefix = raw_key[:8]
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()

        from app.org.models import APIKey  # local import avoids circular

        try:
            key = APIKey.objects.select_related("org_unit", "created_by").get(prefix=prefix, hashed_key=hashed)
        except APIKey.DoesNotExist:
            return None

        if key.expires_at and key.expires_at < timezone.now():
            raise AuthenticationFailed("API key has expired.")

        APIKey.objects.filter(pk=key.pk).update(last_used_at=timezone.now())

        return key.created_by, APIKeyToken(key)


class EmailAuthBackend:
    """Django auth backend that accepts email instead of username."""

    def authenticate(self, request: HttpRequest | None, username: str | None = None, password: str | None = None, **kwargs: object) -> object | None:
        User = get_user_model()
        email = kwargs.get("email") or username
        if not email or not password:
            return None
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None
        return user if user.check_password(password) and user.is_active else None

    def get_user(self, user_id: int) -> object | None:
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class TenantJWTAuthentication:
    """Wraps simplejwt's JWTAuthentication and enforces the tenant claim.

    Loaded by DRF's DEFAULT_AUTHENTICATION_CLASSES — must not import
    simplejwt views/serializers at module level to avoid a circular import.
    """

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
```

**Step 4: Implement jwt_views.py**

Create `backend/app/org/jwt_views.py`:

```python
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
```

**Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/org/test_authentication.py -v
```

Expected: all PASSED.

**Step 6: Commit**

```bash
git add app/org/authentication.py app/org/jwt_views.py tests/org/test_authentication.py
git commit -m "feat: add email auth, API key auth, and tenant-scoped JWT"
```

---

## Task 10: OrgUnit API endpoints

**Files:**
- Create: `backend/app/org/serializers.py`
- Create: `backend/app/org/views.py`
- Create: `backend/app/org/urls.py`
- Create: `backend/tests/org/test_org_api.py`

**Step 1: Write the failing tests**

Create `backend/tests/org/test_org_api.py`:

```python
"""Tests for OrgUnit API endpoints."""

import pytest
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from app.org.models import Membership, OrgUnit, Role, User

TENANTS_CONFIG = [{"slug": "demo", "schema": "demo", "domains": []}]


class OrgUnitAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="alice", email="alice@example.com", password="pass")
        self.client.force_authenticate(user=self.user)
        self.unit = OrgUnit.objects.create(name="Acme Corp", slug="acme", node_type="org")
        Membership.objects.create(user=self.user, org_unit=self.unit, role=Role.OWNER)

    def test_list_org_units(self):
        response = self.client.get("/v1/org/units/")
        assert response.status_code == status.HTTP_200_OK

    def test_create_org_unit(self):
        response = self.client.post("/v1/org/units/", {"name": "Engineering", "slug": "eng", "node_type": "department", "parent": str(self.unit.pk)})
        assert response.status_code == status.HTTP_201_CREATED

    def test_get_org_unit_detail(self):
        response = self.client.get(f"/v1/org/units/{self.unit.pk}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Acme Corp"

    def test_unauthenticated_request_rejected(self):
        client = APIClient()
        response = client.get("/v1/org/units/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/org/test_org_api.py -v
```

**Step 3: Implement serializers**

Create `backend/app/org/serializers.py`:

```python
from __future__ import annotations

from rest_framework import serializers

from app.org.models import APIKey, Membership, OrgUnit, Role, User


class OrgUnitSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = OrgUnit
        fields = ["id", "name", "slug", "node_type", "isolation_policy", "parent", "children"]

    def get_children(self, obj: OrgUnit) -> list:
        return [{"id": str(c.pk), "name": c.name, "slug": c.slug} for c in obj.children.all()]


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ["id", "user", "org_unit", "role"]


class APIKeyCreateSerializer(serializers.ModelSerializer):
    """Write-only serializer — returns the full key once at creation."""

    full_key = serializers.SerializerMethodField()

    class Meta:
        model = APIKey
        fields = ["id", "name", "prefix", "role", "expires_at", "full_key"]
        read_only_fields = ["id", "prefix", "full_key"]

    def get_full_key(self, obj: APIKey) -> str | None:
        return self.context.get("full_key")


class APIKeyListSerializer(serializers.ModelSerializer):
    """Read-only serializer — never returns the full key."""

    class Meta:
        model = APIKey
        fields = ["id", "name", "prefix", "role", "expires_at", "last_used_at"]
```

**Step 4: Implement views**

Create `backend/app/org/views.py`:

```python
from __future__ import annotations

import hashlib
import secrets

from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from app.org.models import APIKey, Membership, OrgUnit
from app.org.serializers import (
    APIKeyCreateSerializer,
    APIKeyListSerializer,
    MembershipSerializer,
    OrgUnitSerializer,
)


class OrgUnitListCreateView(ListCreateAPIView):
    serializer_class = OrgUnitSerializer
    queryset = OrgUnit.objects.all()


class OrgUnitDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = OrgUnitSerializer
    queryset = OrgUnit.objects.all()


class MemberListCreateView(ListCreateAPIView):
    serializer_class = MembershipSerializer

    def get_queryset(self):
        return Membership.objects.filter(org_unit_id=self.kwargs["pk"])


class APIKeyListCreateView(APIView):
    def get(self, request, pk):
        keys = APIKey.objects.filter(org_unit_id=pk)
        return Response(APIKeyListSerializer(keys, many=True).data)

    def post(self, request, pk):
        raw_key = secrets.token_hex(32)
        prefix = raw_key[:8]
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()
        key = APIKey.objects.create(
            name=request.data.get("name", ""),
            prefix=prefix,
            hashed_key=hashed,
            org_unit_id=pk,
            role=request.data.get("role", "member"),
            created_by=request.user,
        )
        serializer = APIKeyCreateSerializer(key, context={"full_key": raw_key})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class APIKeyDeleteView(APIView):
    def delete(self, request, pk, kid):
        APIKey.objects.filter(pk=kid, org_unit_id=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
```

**Step 5: Implement urls**

Create `backend/app/org/urls.py`:

```python
from django.urls import path

from app.org.views import (
    APIKeyDeleteView,
    APIKeyListCreateView,
    MemberListCreateView,
    OrgUnitDetailView,
    OrgUnitListCreateView,
)

urlpatterns = [
    path("units/", OrgUnitListCreateView.as_view(), name="org-unit-list"),
    path("units/<uuid:pk>/", OrgUnitDetailView.as_view(), name="org-unit-detail"),
    path("units/<uuid:pk>/members/", MemberListCreateView.as_view(), name="org-unit-members"),
    path("units/<uuid:pk>/api-keys/", APIKeyListCreateView.as_view(), name="org-unit-api-keys"),
    path("units/<uuid:pk>/api-keys/<uuid:kid>/", APIKeyDeleteView.as_view(), name="org-unit-api-key-delete"),
]
```

**Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/org/test_org_api.py -v
```

**Step 7: Commit**

```bash
git add app/org/serializers.py app/org/views.py app/org/urls.py tests/org/test_org_api.py
git commit -m "feat: add OrgUnit, Membership, and APIKey REST API endpoints"
```

---

## Task 11: seed_tenant management command

**Files:**
- Create: `backend/app/tenants/management/commands/seed_tenant.py`
- Create: `backend/tests/tenants/test_seed_tenant.py`

**Step 1: Write the failing tests**

Create `backend/tests/tenants/test_seed_tenant.py`:

```python
"""Tests for seed_tenant management command."""

from unittest.mock import MagicMock, patch

from django.test import override_settings

TENANTS_CONFIG = [{"slug": "demo", "schema": "demo", "domains": []}]


@override_settings(TENANTS=TENANTS_CONFIG)
@patch("app.tenants.management.commands.seed_tenant.Membership")
@patch("app.tenants.management.commands.seed_tenant.User")
@patch("app.tenants.management.commands.seed_tenant.OrgUnit")
@patch("app.tenants.management.commands.seed_tenant.connection")
def test_seed_tenant_sets_search_path_with_shared(mock_connection, mock_org_unit, mock_user, mock_membership):
    mock_cursor = MagicMock()
    mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_org_unit.objects.get_or_create.return_value = (MagicMock(), True)
    mock_user.objects.get_or_create.return_value = (MagicMock(), False)
    mock_membership.objects.get_or_create.return_value = (MagicMock(), True)

    from app.tenants.management.commands.seed_tenant import Command
    cmd = Command()
    cmd.handle(slug="demo", verbosity=0)

    sql = mock_cursor.execute.call_args[0][0]
    assert "shared" in sql
    assert "demo" in sql
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/tenants/test_seed_tenant.py -v
```

**Step 3: Implement seed_tenant**

Create `backend/app/tenants/management/commands/seed_tenant.py`:

```python
"""Management command: seed_tenant.

Usage:
    uv run manage.py seed_tenant <slug>

Seeds a tenant schema with sample data for demo or development use.
Idempotent: safe to run multiple times.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from app.org.models import Membership, OrgUnit, Role
from app.tenants.utils import safe_schema

User = get_user_model()


class Command(BaseCommand):
    help = "Seed a tenant schema with sample demo data."

    def add_arguments(self, parser) -> None:
        parser.add_argument("slug", type=str)

    def handle(self, *args: object, **options: object) -> None:
        slug: str = options["slug"]
        tenant = next((t for t in settings.TENANTS if t["slug"] == slug), None)
        if tenant is None:
            raise CommandError(f"Tenant '{slug}' not found in TENANTS config.")

        schema = safe_schema(tenant["schema"])
        with connection.cursor() as cursor:
            cursor.execute(f"SET search_path TO {schema}, shared, public")

        corp, _ = OrgUnit.objects.get_or_create(
            slug=f"{slug}-corp",
            defaults={"name": f"{slug.title()} Corp", "node_type": "org"},
        )

        for dept_slug, dept_name in [("engineering", "Engineering"), ("sales", "Sales")]:
            OrgUnit.objects.get_or_create(
                slug=dept_slug,
                parent=corp,
                defaults={"name": dept_name, "node_type": "department"},
            )

        email = f"admin@{slug}.local"
        user, created = User.objects.get_or_create(
            username=email,
            defaults={"email": email, "is_staff": True},
        )
        if created:
            user.set_password("demo-password-change-me")
            user.save()

        Membership.objects.get_or_create(user=user, org_unit=corp, defaults={"role": Role.OWNER})

        if options["verbosity"] > 0:
            self.stdout.write(self.style.SUCCESS(f"Seeded tenant '{slug}'."))
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/tenants/test_seed_tenant.py -v
```

**Step 5: Commit**

```bash
git add app/tenants/management/commands/seed_tenant.py tests/tenants/test_seed_tenant.py
git commit -m "feat: add seed_tenant management command for demo data"
```

---

## Task 12: Full backend test suite pass

**Step 1: Run the full backend test suite**

```bash
cd backend && uv run pytest --tb=short -q
```

Expected: all PASSED, no warnings.

**Step 2: Run linter**

```bash
uv run ruff check . && uv run ruff format --check .
```

Fix any issues:

```bash
uv run ruff check --fix . && uv run ruff format .
```

**Step 3: Commit lint fixes if any**

```bash
git add -u && git commit -m "fix: linting and formatting"
```

---

## Task 13: Next.js frontend setup

**Files:**
- Create: `frontend/` (Next.js project)
- Create: `frontend/Dockerfile`
- Create: `frontend/vitest.config.ts`

**Step 1: Initialise Next.js project**

```bash
cd frontend
npx create-next-app@latest . --typescript --app --no-tailwind --no-eslint --src-dir=false --import-alias="@/*"
```

**Step 2: Add Vitest**

```bash
npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom
```

Create `frontend/vitest.config.ts`:

```typescript
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
  },
});
```

Create `frontend/tests/setup.ts`:

```typescript
import "@testing-library/jest-dom";
```

**Step 3: Write frontend/Dockerfile**

```dockerfile
FROM node:22-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 3000
```

**Step 4: Update package.json scripts**

Ensure `scripts` includes:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "test": "vitest run"
  }
}
```

**Step 5: Commit**

```bash
cd ..
git add frontend/
git commit -m "chore: initialise Next.js frontend with TypeScript and Vitest"
```

---

## Task 14: i18n setup with next-intl

**Files:**
- Create: `frontend/i18n/routing.ts`
- Create: `frontend/i18n/request.ts`
- Create: `frontend/messages/en.json`
- Modify: `frontend/next.config.ts`
- Create: `frontend/middleware.ts`

**Step 1: Install next-intl**

```bash
cd frontend && npm install next-intl
```

**Step 2: Create i18n routing**

Create `frontend/i18n/routing.ts`:

```typescript
import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["en"],
  defaultLocale: "en",
  localePrefix: "as-needed",
});
```

Create `frontend/i18n/request.ts`:

```typescript
import { getRequestConfig } from "next-intl/server";
import { routing } from "./routing";

export default getRequestConfig(async ({ requestLocale }) => {
  const locale = (await requestLocale) ?? routing.defaultLocale;
  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default,
  };
});
```

**Step 3: Create messages/en.json**

```json
{
  "auth": {
    "login": "Login",
    "email": "Email",
    "password": "Password",
    "submit": "Sign in"
  },
  "org": {
    "units": "Org Units",
    "dashboard": "Dashboard"
  }
}
```

**Step 4: Create middleware.ts**

```typescript
import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};
```

**Step 5: Update next.config.ts**

```typescript
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

export default withNextIntl({});
```

**Step 6: Commit**

```bash
cd ..
git add frontend/i18n/ frontend/messages/ frontend/middleware.ts frontend/next.config.ts
git commit -m "feat: add next-intl i18n scaffolding with English-only translations"
```

---

## Task 15: API client, types, and tenant utilities

**Files:**
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/tenant.ts`
- Create: `frontend/types/api.ts`

**Step 1: Write the types**

Create `frontend/types/api.ts`:

```typescript
export interface TokenResponse {
  access: string;
  refresh: string;
}

export interface OrgUnit {
  id: string;
  name: string;
  slug: string;
  node_type: string;
  isolation_policy: "open" | "isolated" | "inherit_only" | "visible_only";
  parent: string | null;
  children: Array<{ id: string; name: string; slug: string }>;
}

export interface Membership {
  id: string;
  user: string;
  org_unit: string;
  role: "owner" | "admin" | "member" | "viewer";
}

export interface ApiError {
  error: { code: string; message: string };
}
```

**Step 2: Write the tenant utility**

Create `frontend/lib/tenant.ts`:

```typescript
interface TenantEntry {
  slug: string;
  schema: string;
  domains: string[];
}

export function getTenantSlugFromHostname(hostname: string): string | null {
  const raw = process.env.NEXT_PUBLIC_TENANTS;
  if (!raw) return null;
  let tenants: TenantEntry[];
  try {
    tenants = JSON.parse(raw) as TenantEntry[];
  } catch {
    return null;
  }
  const host = hostname.split(":")[0];
  return tenants.find((t) => t.domains.includes(host))?.slug ?? null;
}
```

**Step 3: Write the API client**

Create `frontend/lib/api.ts`:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  const body = await res.json();
  if (!res.ok) {
    const err = body?.error ?? { code: "error", message: res.statusText };
    throw new ApiError(err.code, err.message, res.status);
  }
  return body as T;
}

export function obtainToken(slug: string, email: string, password: string) {
  return request<{ access: string; refresh: string }>(`/t/${slug}/v1/auth/token/`, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function listOrgUnits(slug: string, token: string) {
  return request(`/t/${slug}/v1/org/units/`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}
```

**Step 4: Commit**

```bash
cd ..
git add frontend/types/ frontend/lib/
git commit -m "feat: add typed API client, tenant utilities, and TypeScript response types"
```

---

## Task 16: Frontend app structure and login pages

**Files:**
- Create: `frontend/app/(tenant)/[locale]/layout.tsx`
- Create: `frontend/app/(tenant)/[locale]/page.tsx`
- Create: `frontend/app/(tenant)/[locale]/t/[slug]/login/page.tsx`
- Create: `frontend/app/(tenant)/[locale]/login/page.tsx`
- Create: `frontend/app/(tenant)/[locale]/t/[slug]/dashboard/page.tsx`
- Create: `frontend/components/LoginForm.tsx`

**Context:** Two login routes:
- `/t/[slug]/login` — path-prefix mode, used in local development. Slug comes from the URL.
- `/login` — hostname mode, used in production. Slug is resolved from the `Host` header via `getTenantSlugFromHostname`.

Both render the same `LoginForm` client component. After successful login the user is redirected to `/t/[slug]/dashboard`.

**Step 1: Create app route layout**

Create `frontend/app/(tenant)/[locale]/layout.tsx`:

```typescript
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { ReactNode } from "react";

interface Props {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}

export default async function LocaleLayout({ children, params }: Props) {
  const { locale } = await params;
  const messages = await getMessages();
  return (
    <html lang={locale}>
      <body>
        <NextIntlClientProvider messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
```

**Step 2: Create homepage**

Create `frontend/app/(tenant)/[locale]/page.tsx`:

```typescript
export default function HomePage() {
  return <main><h1>Welcome</h1></main>;
}
```

**Step 3: Create LoginForm client component**

Create `frontend/components/LoginForm.tsx`:

```typescript
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { obtainToken } from "@/lib/api";

interface Props {
  slug: string;
}

export default function LoginForm({ slug }: Props) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const { access } = await obtainToken(slug, email, password);
      document.cookie = `access_token=${access}; path=/; SameSite=Lax`;
      router.push(`/t/${slug}/dashboard`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h1>Sign in</h1>
      {error && <p role="alert">{error}</p>}
      <label>
        Email
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      </label>
      <label>
        Password
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      </label>
      <button type="submit">Sign in</button>
    </form>
  );
}
```

**Step 4: Create path-prefix login page**

Create `frontend/app/(tenant)/[locale]/t/[slug]/login/page.tsx`:

```typescript
import LoginForm from "@/components/LoginForm";

interface Props {
  params: Promise<{ slug: string }>;
}

export default async function LoginPage({ params }: Props) {
  const { slug } = await params;
  return <LoginForm slug={slug} />;
}
```

**Step 5: Create hostname-based login page**

Create `frontend/app/(tenant)/[locale]/login/page.tsx`:

```typescript
import { headers } from "next/headers";
import { notFound } from "next/navigation";
import LoginForm from "@/components/LoginForm";
import { getTenantSlugFromHostname } from "@/lib/tenant";

export default async function LoginPage() {
  const host = (await headers()).get("host") ?? "";
  const slug = getTenantSlugFromHostname(host);
  if (!slug) notFound();
  return <LoginForm slug={slug} />;
}
```

**Step 6: Create dashboard page**

Create `frontend/app/(tenant)/[locale]/t/[slug]/dashboard/page.tsx`:

```typescript
interface Props {
  params: Promise<{ slug: string }>;
}

export default async function DashboardPage({ params }: Props) {
  const { slug } = await params;
  return (
    <main>
      <h1>Dashboard</h1>
      <p>Tenant: {slug}</p>
    </main>
  );
}
```

**Step 7: Commit**

```bash
cd ..
git add frontend/app/ frontend/components/
git commit -m "feat: add login pages (path-prefix and hostname) and dashboard"
```

---

## Task 17: Smoke test — Docker Compose up

**Step 1: Tear down any existing volume and start fresh**

```bash
docker compose down -v
docker compose up --build -d
```

**Step 2: Wait for services**

```bash
docker compose ps
```

Expected: all services `running` or `healthy`.

**Step 3: Confirm PostgreSQL init ran correctly**

```bash
# shared schema should exist
docker compose exec db psql -U postgres -d app -c "\dn"

# public should be locked
docker compose exec db psql -U app -d app -c "CREATE TABLE public.test (id int);"
# Expected: ERROR: permission denied for schema public
```

**Step 4: Run database migrations**

```bash
# Migrate shared system tables (auth, contenttypes)
docker compose exec backend uv run manage.py migrate_shared

# Provision tenants
docker compose exec backend uv run manage.py create_tenant acme
docker compose exec backend uv run manage.py create_tenant demo

# Seed demo data
docker compose exec backend uv run manage.py seed_tenant demo
```

**Step 5: Verify login works**

```bash
curl -s http://localhost:8000/t/demo/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@demo.local","password":"demo-password-change-me"}' | python3 -m json.tool
```

Expected: JSON with `access` and `refresh` tokens.

**Step 6: Verify frontend serves**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/t/demo/login
```

Expected: `200`.

**Step 7: Update README.md**

Replace `README.md` with:

```markdown
# Multi-Tenant Application Scaffold

See [design doc](docs/plans/2026-03-07-multi-tenant-scaffold-design.md) for architecture decisions.

## Quick Start

\`\`\`bash
cp .env.example .env
docker compose up --build -d

# First-time database setup
docker compose exec backend uv run manage.py migrate_shared
docker compose exec backend uv run manage.py create_tenant acme
docker compose exec backend uv run manage.py create_tenant demo
docker compose exec backend uv run manage.py seed_tenant demo
\`\`\`

- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- Demo login (dev): http://localhost:3000/t/demo/login
- Demo dashboard: http://localhost:3000/t/demo/dashboard

## Demo credentials

| Email | Password | Role |
|---|---|---|
| admin@demo.local | demo-password-change-me | owner |

## Tenant Management

\`\`\`bash
# Add a new tenant (add entry to TENANTS env var first, then):
docker compose exec backend uv run manage.py create_tenant <slug>

# Fan out pending migrations to all tenants (run after deploy):
docker compose exec backend uv run manage.py migrate_tenants

# Seed a tenant with sample data:
docker compose exec backend uv run manage.py seed_tenant <slug>
\`\`\`

## Schema Layout

\`\`\`
public   ← PostgreSQL system only (locked — no app tables)
shared   ← Django auth, contenttypes, django_migrations (non-tenant)
{tenant} ← All app tables per tenant, own django_migrations
\`\`\`

## Running Tests

\`\`\`bash
# Backend
cd backend && uv run pytest

# Frontend
cd frontend && npm test
\`\`\`
```

**Step 8: Final commit**

```bash
git add README.md
git commit -m "docs: add setup and usage instructions to README"
```

---

## Deferred (document only, do not implement)

- **Background workers (Celery):** Redis broker is ready. Add `celery.py`, Docker Compose worker service, and settings when async tasks are needed.
- **Additional i18n languages:** Add locale to `frontend/i18n/routing.ts`, create `messages/<locale>.json`, extract strings. English URLs unaffected.
- **Self-serve tenant provisioning:** Requires moving tenant config from env var to DB-backed registry and a signup flow.
- **OpenAPI spec generation:** Add `drf-spectacular` and generate TypeScript types from the schema for `frontend/types/api.ts`.
