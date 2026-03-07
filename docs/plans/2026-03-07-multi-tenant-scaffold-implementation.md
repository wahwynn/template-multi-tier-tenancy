# Multi-Tenant Scaffold Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Scaffold a full-stack multi-tenant application with PostgreSQL schema-per-tenant isolation, unlimited-depth org hierarchy, flexible role-based membership, and API key authentication.

**Architecture:** Django backend with custom tenant middleware that reads tenant config from an env var (12-factor), sets PostgreSQL `search_path` per request. Each tenant schema contains `OrgUnit` (self-referential tree with `isolation_policy`), `Membership`, and `APIKey` tables. Next.js frontend with JWT auth and `next-intl` i18n scaffolding.

**Tech Stack:** Django 5.x, DRF, djangorestframework-simplejwt, PostgreSQL 16, Redis 7, Next.js 15 (App Router), TypeScript, next-intl, Docker Compose, pytest, Vitest, uv

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
- Create: `backend/` (directory)
- Create: `frontend/` (directory)

**Step 1: Update PROJECT.md with stack decisions**

Replace the contents of `PROJECT.md`:

```markdown
# Project Metadata

- **Project type**: full-stack
- **Backend framework**: Django 5.x + Django REST Framework
- **Frontend framework**: Next.js 15 (App Router) + TypeScript
- **Database**: PostgreSQL 16 (schema-per-tenant isolation)
- **Cache**: Redis 7

## Project Structure

\`\`\`
frontend/          ← Next.js frontend
backend/           ← Django backend
docker-compose.yml ← Local development orchestration
\`\`\`

See `docs/plans/2026-03-07-multi-tenant-scaffold-design.md` for full architecture decisions.
```

**Step 2: Create top-level directories**

```bash
mkdir -p backend frontend
```

**Step 3: Commit**

```bash
git add PROJECT.md backend/.gitkeep frontend/.gitkeep
git commit -m "chore: establish project structure and update PROJECT.md"
```

---

## Task 2: Docker Compose and environment config

**Files:**
- Modify: `docker-compose.yml`
- Create: `.env.example`

**Step 1: Write docker-compose.yml**

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
      - JWT_SECRET=${JWT_SECRET}
      - JWT_ACCESS_TOKEN_EXPIRY=${JWT_ACCESS_TOKEN_EXPIRY:-3600}
      - JWT_REFRESH_TOKEN_EXPIRY=${JWT_REFRESH_TOKEN_EXPIRY:-86400}
      - DEBUG=${DEBUG:-true}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
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
      - NEXT_PUBLIC_API_URL=http://localhost:8000
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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

**Step 2: Write .env.example**

```bash
# Tenant configuration (JSON array)
# Each tenant: slug (URL identifier), schema (PostgreSQL schema name),
# domains (list of hostnames), demo (optional bool for seed data)
TENANTS='[{"slug":"acme","schema":"acme","domains":["acme.localhost"],"demo":false},{"slug":"demo","schema":"demo","domains":[],"demo":true}]'

# Database
DATABASE_URL=postgres://app:app@localhost:5432/app

# Redis
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_SECRET=change-me-in-production-use-a-long-random-string
JWT_ACCESS_TOKEN_EXPIRY=3600
JWT_REFRESH_TOKEN_EXPIRY=86400

# Django
DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

**Step 3: Copy .env.example to .env**

```bash
cp .env.example .env
```

**Step 4: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "chore: add Docker Compose services and env config"
```

---

## Task 3: Django project setup

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/manage.py`
- Create: `backend/config/` (Django project package)
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`

**Step 1: Initialise Django project with uv**

```bash
cd backend
uv init --no-readme --python 3.14
uv add django djangorestframework djangorestframework-simplejwt psycopg[binary] redis django-redis pydantic-settings
uv add --dev pytest pytest-django pytest-cov factory-boy ruff
```

**Step 2: Create Django project**

```bash
uv run django-admin startproject config .
```

This creates `manage.py` and `config/` (with `settings.py`, `urls.py`, `wsgi.py`, `asgi.py`).

**Step 3: Replace config/settings.py**

```python
"""Django settings for multi-tenant scaffold."""

from __future__ import annotations

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Security ---
SECRET_KEY: str = os.environ["JWT_SECRET"]
DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"
ALLOWED_HOSTS: list[str] = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# --- Tenants (12-factor: loaded from env, never from DB) ---
TENANTS: list[dict] = json.loads(os.environ.get("TENANTS", "[]"))

# --- Installed apps ---
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "rest_framework_simplejwt",
    "app.tenants",
    "app.org",
]

# --- Middleware ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "app.tenants.middleware.TenantMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

# --- Database ---
import dj_database_url  # noqa: E402  (added below)
DATABASES = {
    "default": dj_database_url.parse(os.environ["DATABASE_URL"])
}

# --- Cache / Sessions ---
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

# --- Auth ---
AUTH_USER_MODEL = "auth.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "app.org.authentication.APIKeyAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.CursorPagination",
    "PAGE_SIZE": 50,
    "EXCEPTION_HANDLER": "app.tenants.exceptions.custom_exception_handler",
}

from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(seconds=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRY", "3600"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(seconds=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRY", "86400"))),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en-us"
USE_TZ = True
```

**Step 4: Add `dj-database-url` dependency**

```bash
uv add dj-database-url
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

**Step 6: Write backend/.dockerignore**

```
__pycache__
*.pyc
*.pyo
.env
.venv
.pytest_cache
htmlcov
.coverage
```

**Step 7: Write backend/pytest.ini**

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

**Step 8: Create app package directories**

```bash
mkdir -p app/tenants app/org
touch app/__init__.py app/tenants/__init__.py app/org/__init__.py
```

**Step 9: Commit**

```bash
git add backend/
git commit -m "chore: initialise Django project with uv and core settings"
```

---

## Task 4: Tenant middleware

**Files:**
- Create: `backend/app/tenants/middleware.py`
- Create: `backend/tests/tenants/test_middleware.py`

**Step 1: Write the failing test**

Create `backend/tests/__init__.py`, `backend/tests/tenants/__init__.py`, then write `backend/tests/tenants/test_middleware.py`:

```python
"""Tests for TenantMiddleware."""

import pytest
from django.test import RequestFactory, override_settings
from django.http import Http404

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


@override_settings(TENANTS=TENANTS_CONFIG)
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
```

**Step 2: Run test to verify it fails**

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
            schema = request.tenant["schema"]
            cursor.execute(f"SET search_path TO {schema}, public")  # noqa: S608
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
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/tenants/test_middleware.py -v
```

Expected: 4 PASSED.

**Step 5: Commit**

```bash
git add app/tenants/middleware.py tests/tenants/
git commit -m "feat: add TenantMiddleware with path-prefix and domain resolution"
```

---

## Task 5: Custom exception handler

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

Expected: FAILED.

**Step 3: Implement exception handler**

Create `backend/app/tenants/exceptions.py`:

```python
"""Consistent error response shape for all API endpoints.

All error responses follow: ``{"error": {"code": "...", "message": "..."}}``.
"""

from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context) -> Response | None:
    """Wrap DRF exceptions in a consistent ``{"error": {...}}`` envelope."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    # Flatten DRF's detail into a single message string.
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
        422: "unprocessable_entity",
        429: "too_many_requests",
        500: "internal_server_error",
    }
    return mapping.get(status_code, "error")
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/tenants/test_exceptions.py -v
```

Expected: 2 PASSED.

**Step 5: Commit**

```bash
git add app/tenants/exceptions.py tests/tenants/test_exceptions.py
git commit -m "feat: add consistent API error response format"
```

---

## Task 6: Management commands — create_tenant and migrate_tenants

**Files:**
- Create: `backend/app/tenants/management/__init__.py`
- Create: `backend/app/tenants/management/commands/__init__.py`
- Create: `backend/app/tenants/management/commands/create_tenant.py`
- Create: `backend/app/tenants/management/commands/migrate_tenants.py`
- Create: `backend/tests/tenants/test_management_commands.py`

**Step 1: Write the failing tests**

```python
"""Tests for tenant management commands."""

import pytest
from django.test import TestCase, override_settings
from unittest.mock import MagicMock, call, patch

from app.tenants.management.commands.create_tenant import Command as CreateTenantCommand
from app.tenants.management.commands.migrate_tenants import Command as MigrateTenantsCommand

TENANTS_CONFIG = [
    {"slug": "acme", "schema": "acme", "domains": ["acme.localhost"]},
    {"slug": "demo", "schema": "demo", "domains": []},
]


@override_settings(TENANTS=TENANTS_CONFIG)
@patch("app.tenants.management.commands.create_tenant.connection")
@patch("app.tenants.management.commands.create_tenant.call_command")
def test_create_tenant_creates_schema_and_runs_migrations(mock_call_command, mock_connection):
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
    with pytest.raises(SystemExit):
        cmd.handle(slug="unknown", verbosity=1)


@override_settings(TENANTS=TENANTS_CONFIG)
@patch("app.tenants.management.commands.migrate_tenants.connection")
@patch("app.tenants.management.commands.migrate_tenants.call_command")
def test_migrate_tenants_runs_migrate_for_all_tenants(mock_call_command, mock_connection):
    mock_cursor = MagicMock()
    mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=False)

    cmd = MigrateTenantsCommand()
    cmd.handle(schema=None, verbosity=1)

    assert mock_call_command.call_count == 2
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/tenants/test_management_commands.py -v
```

Expected: FAILED.

**Step 3: Implement create_tenant command**

```python
"""Management command: create_tenant.

Usage:
    uv run manage.py create_tenant <slug>

Creates the PostgreSQL schema for the given tenant slug and runs
migrations into it.
"""

from __future__ import annotations

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Create a PostgreSQL schema for a tenant and run migrations."

    def add_arguments(self, parser) -> None:
        parser.add_argument("slug", type=str, help="Tenant slug (must exist in TENANTS config)")

    def handle(self, *args, **options) -> None:
        slug: str = options["slug"]
        tenant = next((t for t in settings.TENANTS if t["slug"] == slug), None)
        if tenant is None:
            raise CommandError(f"Tenant '{slug}' not found in TENANTS config.")

        schema = tenant["schema"]
        self.stdout.write(f"Creating schema '{schema}'...")
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

        self.stdout.write(f"Running migrations for schema '{schema}'...")
        call_command("migrate_tenants", "--schema", schema, verbosity=options["verbosity"])
        self.stdout.write(self.style.SUCCESS(f"Tenant '{slug}' ready."))
```

**Step 4: Implement migrate_tenants command**

```python
"""Management command: migrate_tenants.

Usage:
    uv run manage.py migrate_tenants              # all tenants
    uv run manage.py migrate_tenants --schema acme  # one tenant

Fans out Django's ``migrate`` command across all (or one) tenant schemas.
Safe to re-run: each schema tracks its own django_migrations state.
"""

from __future__ import annotations

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Run Django migrations across all (or one) tenant schemas."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--schema",
            type=str,
            default=None,
            help="Limit to a single schema. Defaults to all tenants.",
        )

    def handle(self, *args, **options) -> None:
        target_schema: str | None = options.get("schema")

        tenants = settings.TENANTS
        if target_schema:
            tenants = [t for t in tenants if t["schema"] == target_schema]

        for tenant in tenants:
            schema = tenant["schema"]
            self.stdout.write(f"Migrating schema '{schema}'...")
            with connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {schema}, public")  # noqa: S608
            try:
                call_command("migrate", verbosity=options["verbosity"])
                self.stdout.write(self.style.SUCCESS(f"  '{schema}' OK"))
            except Exception as exc:  # noqa: BLE001
                self.stderr.write(self.style.ERROR(f"  '{schema}' FAILED: {exc}"))
                raise
```

**Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/tenants/test_management_commands.py -v
```

Expected: 3 PASSED.

**Step 6: Commit**

```bash
git add app/tenants/management/ tests/tenants/test_management_commands.py
git commit -m "feat: add create_tenant and migrate_tenants management commands"
```

---

## Task 7: OrgUnit model

**Files:**
- Create: `backend/app/org/models.py`
- Create: `backend/app/org/apps.py`
- Create: `backend/tests/org/__init__.py`
- Create: `backend/tests/org/test_org_unit.py`

**Step 1: Write the failing test**

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

    def test_slug_unique_within_parent(self):
        from django.db import IntegrityError
        parent = OrgUnit.objects.create(name="Acme Corp", slug="acme", node_type="org")
        OrgUnit.objects.create(name="Eng", slug="eng", node_type="department", parent=parent)
        with pytest.raises(IntegrityError):
            OrgUnit.objects.create(name="Eng2", slug="eng", node_type="department", parent=parent)

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

Expected: FAILED — models do not exist.

**Step 3: Implement OrgUnit model**

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
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db import models

if TYPE_CHECKING:
    from django.db.models import QuerySet


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
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "parent"],
                name="unique_slug_within_parent",
                condition=models.Q(parent__isnull=False),
            )
        ]

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

    def get_descendants(self) -> QuerySet[OrgUnit]:
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
        return OrgUnit.objects.filter(pk__in=ids)


class Membership(models.Model):
    """Explicit membership of a User in an OrgUnit with a role."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        get_user_model(),
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
        constraints = [
            models.UniqueConstraint(fields=["user", "org_unit"], name="unique_user_org_unit")
        ]

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
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_api_keys",
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["prefix", "hashed_key"], name="unique_api_key")
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.prefix}...)"
```

**Step 4: Create app config**

Create `backend/app/org/apps.py`:

```python
from django.apps import AppConfig


class OrgConfig(AppConfig):
    name = "app.org"
    label = "app_org"
```

**Step 5: Create and run migrations**

```bash
uv run manage.py makemigrations app_org
```

**Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/org/test_org_unit.py -v
```

Expected: all PASSED.

**Step 7: Commit**

```bash
git add app/org/ tests/org/
git commit -m "feat: add OrgUnit, Membership, and APIKey models"
```

---

## Task 8: API key authentication backend

**Files:**
- Create: `backend/app/org/authentication.py`
- Create: `backend/tests/org/test_authentication.py`

**Step 1: Write the failing test**

```python
"""Tests for API key authentication."""

import hashlib
import secrets

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
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
        request = self.factory.get("/", HTTP_AUTHORIZATION="Bearer invalidkey123456")
        auth = APIKeyAuthentication()
        result = auth.authenticate(request)
        assert result is None

    def test_expired_api_key_raises_auth_error(self):
        from rest_framework.exceptions import AuthenticationFailed
        self.api_key.expires_at = timezone.now() - timezone.timedelta(hours=1)
        self.api_key.save()
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {self.raw_key}")
        auth = APIKeyAuthentication()
        with pytest.raises(AuthenticationFailed):
            auth.authenticate(request)

    def test_jwt_bearer_token_is_skipped(self):
        # JWT tokens are long; API key auth should not try to handle them.
        request = self.factory.get("/", HTTP_AUTHORIZATION="Bearer eyJhbGciOiJIUzI1NiJ9.fake.jwt")
        auth = APIKeyAuthentication()
        result = auth.authenticate(request)
        assert result is None
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/org/test_authentication.py -v
```

**Step 3: Implement APIKeyAuthentication**

Create `backend/app/org/authentication.py`:

```python
"""API key authentication backend for Django REST Framework.

API keys use the same ``Authorization: Bearer <key>`` header as JWTs.
This backend is checked first; it returns ``None`` for JWT-shaped tokens
so that simplejwt can handle them.

Keys are identified by their 8-character prefix, then verified by
comparing the SHA-256 hash of the full key against the stored hash.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

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

    _JWT_MIN_LENGTH = 100  # JWTs are always long; skip short tokens to simplejwt

    def authenticate(self, request: HttpRequest) -> tuple | None:
        header: str = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None

        raw_key = header[len("Bearer "):]

        # Heuristic: JWTs contain dots; raw hex keys do not.
        if "." in raw_key or len(raw_key) >= self._JWT_MIN_LENGTH:
            return None  # Let simplejwt handle it.

        if len(raw_key) < 8:  # noqa: PLR2004
            return None

        prefix = raw_key[:8]
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()

        from app.org.models import APIKey  # local import avoids circular

        try:
            key = APIKey.objects.select_related("org_unit", "created_by").get(
                prefix=prefix, hashed_key=hashed
            )
        except APIKey.DoesNotExist:
            return None

        if key.expires_at and key.expires_at < timezone.now():
            raise AuthenticationFailed("API key has expired.")

        # Update last_used_at without triggering full model save overhead.
        APIKey.objects.filter(pk=key.pk).update(last_used_at=timezone.now())

        # Return the key's creator as the user for permission checks.
        return key.created_by, APIKeyToken(key)
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/org/test_authentication.py -v
```

Expected: all PASSED.

**Step 5: Commit**

```bash
git add app/org/authentication.py tests/org/test_authentication.py
git commit -m "feat: add API key authentication backend"
```

---

## Task 9: OrgUnit API endpoints

**Files:**
- Create: `backend/app/org/serializers.py`
- Create: `backend/app/org/views.py`
- Create: `backend/app/org/urls.py`
- Modify: `backend/config/urls.py`
- Create: `backend/tests/org/test_org_api.py`

**Step 1: Write the failing tests**

```python
"""Tests for OrgUnit API endpoints."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from app.org.models import Membership, OrgUnit, Role

User = get_user_model()

TENANTS_CONFIG = [{"slug": "acme", "schema": "acme", "domains": []}]


@override_settings(TENANTS=TENANTS_CONFIG)
class TestOrgUnitAPI(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="alice", password="pass", email="alice@example.com")
        self.corp = OrgUnit.objects.create(name="Acme Corp", slug="acme-corp", node_type="org")
        Membership.objects.create(user=self.user, org_unit=self.corp, role=Role.ADMIN)
        self.client.force_authenticate(user=self.user)

    def test_list_org_units_returns_accessible_units(self):
        response = self.client.get("/v1/org/units/")
        assert response.status_code == 200
        slugs = [u["slug"] for u in response.data["results"]]
        assert "acme-corp" in slugs

    def test_create_org_unit(self):
        response = self.client.post("/v1/org/units/", {
            "name": "Engineering",
            "slug": "engineering",
            "node_type": "department",
            "parent": str(self.corp.pk),
            "isolation_policy": "open",
        }, format="json")
        assert response.status_code == 201
        assert response.data["slug"] == "engineering"

    def test_get_org_unit_detail(self):
        response = self.client.get(f"/v1/org/units/{self.corp.pk}/")
        assert response.status_code == 200
        assert response.data["name"] == "Acme Corp"

    def test_get_ancestors(self):
        dept = OrgUnit.objects.create(name="Dept", slug="dept", parent=self.corp)
        response = self.client.get(f"/v1/org/units/{dept.pk}/ancestors/")
        assert response.status_code == 200
        assert any(u["slug"] == "acme-corp" for u in response.data)

    def test_get_descendants(self):
        dept = OrgUnit.objects.create(name="Dept", slug="dept", parent=self.corp)
        response = self.client.get(f"/v1/org/units/{self.corp.pk}/descendants/")
        assert response.status_code == 200
        assert any(u["slug"] == "dept" for u in response.data)

    def test_unauthenticated_request_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/v1/org/units/")
        assert response.status_code == 401
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/org/test_org_api.py -v
```

**Step 3: Implement serializers**

Create `backend/app/org/serializers.py`:

```python
"""DRF serializers for org hierarchy models."""

from __future__ import annotations

from rest_framework import serializers

from app.org.models import APIKey, Membership, OrgUnit


class OrgUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgUnit
        fields = ["id", "name", "slug", "parent", "node_type", "isolation_policy"]


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ["id", "user", "org_unit", "role"]


class APIKeyCreateSerializer(serializers.ModelSerializer):
    """Used only on creation — returns the full raw key once."""
    raw_key = serializers.CharField(read_only=True)

    class Meta:
        model = APIKey
        fields = ["id", "name", "org_unit", "role", "expires_at", "raw_key"]


class APIKeyListSerializer(serializers.ModelSerializer):
    """Safe for listing — never exposes the key."""
    class Meta:
        model = APIKey
        fields = ["id", "name", "prefix", "org_unit", "role", "expires_at", "last_used_at"]
```

**Step 4: Implement views**

Create `backend/app/org/views.py`:

```python
"""API views for the org hierarchy."""

from __future__ import annotations

import hashlib
import secrets

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from app.org.models import APIKey, Membership, OrgUnit
from app.org.serializers import (
    APIKeyCreateSerializer,
    APIKeyListSerializer,
    MembershipSerializer,
    OrgUnitSerializer,
)


class OrgUnitViewSet(ModelViewSet):
    serializer_class = OrgUnitSerializer

    def get_queryset(self):
        # Return only units the current user has explicit membership in.
        user = self.request.user
        member_unit_ids = Membership.objects.filter(user=user).values_list("org_unit_id", flat=True)
        return OrgUnit.objects.filter(pk__in=member_unit_ids)

    @action(detail=True, methods=["get"])
    def ancestors(self, request: Request, pk=None) -> Response:
        unit = self.get_object()
        serializer = OrgUnitSerializer(unit.get_ancestors(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def descendants(self, request: Request, pk=None) -> Response:
        unit = self.get_object()
        serializer = OrgUnitSerializer(unit.get_descendants(), many=True)
        return Response(serializer.data)


class MembershipViewSet(ModelViewSet):
    serializer_class = MembershipSerializer

    def get_queryset(self):
        return Membership.objects.filter(org_unit_id=self.kwargs["unit_pk"])


class APIKeyViewSet(ModelViewSet):
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return APIKeyCreateSerializer
        return APIKeyListSerializer

    def get_queryset(self):
        return APIKey.objects.filter(org_unit_id=self.kwargs["unit_pk"])

    def create(self, request: Request, unit_pk=None) -> Response:
        raw_key = secrets.token_hex(32)
        prefix = raw_key[:8]
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()

        serializer = APIKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = serializer.save(
            prefix=prefix,
            hashed_key=hashed,
            created_by=request.user,
            org_unit_id=unit_pk,
        )
        data = APIKeyCreateSerializer(key).data
        data["raw_key"] = raw_key
        return Response(data, status=status.HTTP_201_CREATED)
```

**Step 5: Implement URLs**

Create `backend/app/org/urls.py`:

```python
from rest_framework_nested import routers
from rest_framework.routers import DefaultRouter

from app.org.views import APIKeyViewSet, MembershipViewSet, OrgUnitViewSet

router = DefaultRouter()
router.register("units", OrgUnitViewSet, basename="org-unit")

units_router = routers.NestedDefaultRouter(router, "units", lookup="unit")
units_router.register("members", MembershipViewSet, basename="org-unit-members")
units_router.register("api-keys", APIKeyViewSet, basename="org-unit-api-keys")

urlpatterns = router.urls + units_router.urls
```

Add `drf-nested-routers` dependency:

```bash
uv add drf-nested-routers
```

Update `backend/config/urls.py`:

```python
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("v1/auth/token/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("v1/org/", include("app.org.urls")),
]
```

**Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/org/test_org_api.py -v
```

Expected: all PASSED.

**Step 7: Commit**

```bash
git add app/org/serializers.py app/org/views.py app/org/urls.py config/urls.py tests/org/test_org_api.py
git commit -m "feat: add OrgUnit, Membership, and APIKey REST API endpoints"
```

---

## Task 10: seed_tenant management command

**Files:**
- Create: `backend/app/tenants/management/commands/seed_tenant.py`
- Create: `backend/tests/tenants/test_seed_tenant.py`

**Step 1: Write the failing test**

```python
"""Tests for seed_tenant management command."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from app.tenants.management.commands.seed_tenant import Command
from app.org.models import Membership, OrgUnit

User = get_user_model()

TENANTS_CONFIG = [{"slug": "demo", "schema": "demo", "domains": [], "demo": True}]


@override_settings(TENANTS=TENANTS_CONFIG)
class TestSeedTenant(TestCase):
    def test_seed_creates_root_org_unit(self):
        cmd = Command()
        cmd.handle(slug="demo", verbosity=0)
        assert OrgUnit.objects.filter(slug="demo-corp").exists()

    def test_seed_creates_admin_user(self):
        cmd = Command()
        cmd.handle(slug="demo", verbosity=0)
        assert User.objects.filter(username="admin@demo.local").exists()

    def test_seed_is_idempotent(self):
        cmd = Command()
        cmd.handle(slug="demo", verbosity=0)
        cmd.handle(slug="demo", verbosity=0)
        assert OrgUnit.objects.filter(slug="demo-corp").count() == 1
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/tenants/test_seed_tenant.py -v
```

**Step 3: Implement seed_tenant command**

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

User = get_user_model()


class Command(BaseCommand):
    help = "Seed a tenant schema with sample demo data."

    def add_arguments(self, parser) -> None:
        parser.add_argument("slug", type=str)

    def handle(self, *args, **options) -> None:
        slug: str = options["slug"]
        tenant = next((t for t in settings.TENANTS if t["slug"] == slug), None)
        if tenant is None:
            raise CommandError(f"Tenant '{slug}' not found in TENANTS config.")

        schema = tenant["schema"]
        with connection.cursor() as cursor:
            cursor.execute(f"SET search_path TO {schema}, public")  # noqa: S608

        # Root org unit
        corp, _ = OrgUnit.objects.get_or_create(
            slug=f"{slug}-corp",
            defaults={"name": f"{slug.title()} Corp", "node_type": "org"},
        )

        # Demo departments
        for dept_slug, dept_name in [("engineering", "Engineering"), ("sales", "Sales")]:
            OrgUnit.objects.get_or_create(
                slug=dept_slug,
                parent=corp,
                defaults={"name": dept_name, "node_type": "department"},
            )

        # Admin user
        email = f"admin@{slug}.local"
        user, created = User.objects.get_or_create(
            username=email,
            defaults={"email": email, "is_staff": True},
        )
        if created:
            user.set_password("demo-password-change-me")
            user.save()

        Membership.objects.get_or_create(
            user=user, org_unit=corp, defaults={"role": Role.OWNER}
        )

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

## Task 11: Full backend test suite pass

**Step 1: Run the full backend test suite**

```bash
uv run pytest --tb=short -q
```

Expected: all PASSED, no warnings about missing migrations.

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
git add -u
git commit -m "chore: fix linting issues"
```

---

## Task 12: Next.js frontend setup

**Files:**
- Create: `frontend/` (Next.js project)
- Create: `frontend/Dockerfile`
- Create: `frontend/.dockerignore`

**Step 1: Initialise Next.js project**

```bash
cd frontend
npx create-next-app@latest . \
  --typescript \
  --eslint \
  --app \
  --no-src-dir \
  --import-alias "@/*" \
  --no-tailwind
```

When prompted, accept defaults.

**Step 2: Install dependencies**

```bash
npm install next-intl
npm install --save-dev @types/node vitest @vitejs/plugin-react @testing-library/react @testing-library/dom jsdom
```

**Step 3: Write frontend/Dockerfile**

```dockerfile
FROM node:22-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM node:22-alpine AS runner
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]
```

**Step 4: Write frontend/.dockerignore**

```
node_modules
.next
.env.local
*.log
```

**Step 5: Add vitest config**

Create `frontend/vitest.config.ts`:

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./tests/setup.ts",
  },
});
```

Create `frontend/tests/setup.ts`:

```typescript
import "@testing-library/dom";
```

Add test script to `frontend/package.json`:

```json
"scripts": {
  "test": "vitest run",
  "test:watch": "vitest"
}
```

**Step 6: Commit**

```bash
cd ..
git add frontend/
git commit -m "chore: initialise Next.js frontend with TypeScript and Vitest"
```

---

## Task 13: i18n setup with next-intl

**Files:**
- Create: `frontend/i18n/routing.ts`
- Create: `frontend/i18n/request.ts`
- Create: `frontend/messages/en.json`
- Modify: `frontend/next.config.ts`
- Modify: `frontend/middleware.ts`

**Step 1: Write the failing test**

Create `frontend/tests/i18n/routing.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { routing } from "@/i18n/routing";

describe("i18n routing", () => {
  it("defaults to English locale", () => {
    expect(routing.defaultLocale).toBe("en");
  });

  it("uses as-needed prefix so English URLs have no locale segment", () => {
    expect(routing.localePrefix).toBe("as-needed");
  });

  it("includes English in supported locales", () => {
    expect(routing.locales).toContain("en");
  });
});
```

**Step 2: Run test to verify it fails**

```bash
cd frontend && npm test
```

Expected: FAILED.

**Step 3: Implement i18n routing config**

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

Create `frontend/messages/en.json`:

```json
{
  "common": {
    "loading": "Loading...",
    "error": "An error occurred",
    "save": "Save",
    "cancel": "Cancel",
    "delete": "Delete"
  },
  "auth": {
    "login": "Log in",
    "logout": "Log out",
    "email": "Email",
    "password": "Password"
  },
  "org": {
    "units": "Organisation Units",
    "members": "Members",
    "apiKeys": "API Keys",
    "addMember": "Add Member",
    "createUnit": "Create Unit"
  }
}
```

Update `frontend/next.config.ts`:

```typescript
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

const nextConfig = withNextIntl({});

export default nextConfig;
```

Create `frontend/middleware.ts`:

```typescript
import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};
```

**Step 4: Run tests to verify they pass**

```bash
npm test
```

Expected: PASSED.

**Step 5: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat: add next-intl i18n scaffolding with English-only translations"
```

---

## Task 14: API client and types

**Files:**
- Create: `frontend/types/api.ts`
- Create: `frontend/lib/api.ts`
- Create: `frontend/tests/lib/api.test.ts`

**Step 1: Write the failing test**

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("API client", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("sends Authorization header when token is provided", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ results: [] }),
    });

    const { createApiClient } = await import("@/lib/api");
    const client = createApiClient({ baseUrl: "http://localhost:8000", token: "test-token" });
    await client.get("/v1/org/units/");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/org/units/",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer test-token" }),
      })
    );
  });

  it("throws ApiError with error code on non-2xx response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ error: { code: "not_found", message: "Not found" } }),
    });

    const { createApiClient, ApiError } = await import("@/lib/api");
    const client = createApiClient({ baseUrl: "http://localhost:8000" });
    await expect(client.get("/v1/org/units/999/")).rejects.toThrow(ApiError);
  });
});
```

**Step 2: Run test to verify it fails**

```bash
cd frontend && npm test
```

**Step 3: Implement types and API client**

Create `frontend/types/api.ts`:

```typescript
export type IsolationPolicy = "open" | "isolated" | "inherit_only" | "visible_only";
export type Role = "owner" | "admin" | "member" | "viewer";

export interface OrgUnit {
  id: string;
  name: string;
  slug: string;
  parent: string | null;
  node_type: string;
  isolation_policy: IsolationPolicy;
}

export interface Membership {
  id: string;
  user: number;
  org_unit: string;
  role: Role;
}

export interface APIKeyList {
  id: string;
  name: string;
  prefix: string;
  org_unit: string;
  role: Role;
  expires_at: string | null;
  last_used_at: string | null;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiErrorBody {
  error: { code: string; message: string };
}
```

Create `frontend/lib/api.ts`:

```typescript
import type { ApiErrorBody } from "@/types/api";

interface ClientConfig {
  baseUrl: string;
  token?: string;
}

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function createApiClient(config: ClientConfig) {
  const headers = (): Record<string, string> => ({
    "Content-Type": "application/json",
    ...(config.token ? { Authorization: `Bearer ${config.token}` } : {}),
  });

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${config.baseUrl}${path}`, {
      ...init,
      headers: { ...headers(), ...init?.headers },
    });

    if (!response.ok) {
      const body: ApiErrorBody = await response.json();
      throw new ApiError(body.error.code, body.error.message, response.status);
    }

    return response.json() as Promise<T>;
  }

  return {
    get: <T>(path: string) => request<T>(path),
    post: <T>(path: string, body: unknown) =>
      request<T>(path, { method: "POST", body: JSON.stringify(body) }),
    patch: <T>(path: string, body: unknown) =>
      request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
    delete: (path: string) => request<void>(path, { method: "DELETE" }),
  };
}
```

**Step 4: Run tests to verify they pass**

```bash
npm test
```

Expected: all PASSED.

**Step 5: Commit**

```bash
cd ..
git add frontend/types/ frontend/lib/ frontend/tests/
git commit -m "feat: add typed API client and TypeScript response types"
```

---

## Task 15: Frontend app structure and login page

**Files:**
- Create: `frontend/app/(auth)/login/page.tsx`
- Create: `frontend/app/(tenant)/[locale]/layout.tsx`
- Create: `frontend/app/(tenant)/[locale]/dashboard/page.tsx`
- Create: `frontend/tests/app/login.test.tsx`

**Step 1: Write the failing test**

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import LoginPage from "@/app/(auth)/login/page";

// Mock next-intl
vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

describe("LoginPage", () => {
  it("renders email and password fields", () => {
    render(<LoginPage />);
    expect(screen.getByLabelText(/email/i)).toBeDefined();
    expect(screen.getByLabelText(/password/i)).toBeDefined();
  });

  it("renders a submit button", () => {
    render(<LoginPage />);
    expect(screen.getByRole("button", { name: /log in/i })).toBeDefined();
  });
});
```

**Step 2: Run test to verify it fails**

```bash
cd frontend && npm test
```

**Step 3: Create app directory structure and login page**

Create `frontend/app/(auth)/login/page.tsx`:

```tsx
"use client";

import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

export default function LoginPage() {
  const t = useTranslations("auth");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (res.ok) {
      window.location.href = "/dashboard";
    }
  }

  return (
    <main>
      <h1>{t("login")}</h1>
      <form onSubmit={handleSubmit}>
        <label htmlFor="email">{t("email")}</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <label htmlFor="password">{t("password")}</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button type="submit">{t("login")}</button>
      </form>
    </main>
  );
}
```

Create `frontend/app/(tenant)/[locale]/layout.tsx`:

```tsx
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";

interface Props {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}

export default async function TenantLayout({ children, params }: Props) {
  const { locale } = await params;
  const messages = await getMessages();

  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
      {children}
    </NextIntlClientProvider>
  );
}
```

Create `frontend/app/(tenant)/[locale]/dashboard/page.tsx`:

```tsx
import { useTranslations } from "next-intl";

export default function DashboardPage() {
  const t = useTranslations("org");
  return (
    <main>
      <h1>{t("units")}</h1>
    </main>
  );
}
```

**Step 4: Run tests to verify they pass**

```bash
npm test
```

Expected: all PASSED.

**Step 5: Commit**

```bash
cd ..
git add frontend/app/ frontend/tests/app/
git commit -m "feat: add login page and tenant layout with i18n"
```

---

## Task 16: Smoke test — Docker Compose up

**Step 1: Start all services**

```bash
docker compose up --build -d
```

**Step 2: Wait for services to be healthy**

```bash
docker compose ps
```

Expected: all services `running` or `healthy`.

**Step 3: Run database migrations**

```bash
docker compose exec backend uv run manage.py migrate
docker compose exec backend uv run manage.py create_tenant acme
docker compose exec backend uv run manage.py create_tenant demo
docker compose exec backend uv run manage.py seed_tenant demo
```

**Step 4: Verify backend API responds**

```bash
curl -s http://localhost:8000/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@demo.local","password":"demo-password-change-me"}' | python3 -m json.tool
```

Expected: JSON response with `access` and `refresh` tokens.

**Step 5: Verify frontend serves**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

Expected: `200`.

**Step 6: Tear down**

```bash
docker compose down
```

**Step 7: Update README.md with setup instructions**

Update `README.md` with:

```markdown
# Multi-Tenant Application Scaffold

See [design doc](docs/plans/2026-03-07-multi-tenant-scaffold-design.md) for architecture decisions.

## Quick Start

\`\`\`bash
cp .env.example .env
docker compose up --build -d
docker compose exec backend uv run manage.py create_tenant acme
docker compose exec backend uv run manage.py create_tenant demo
docker compose exec backend uv run manage.py seed_tenant demo
\`\`\`

- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- Demo tenant (path prefix): http://localhost:3000/t/demo/dashboard

## Tenant Management

\`\`\`bash
# Add a new tenant (add entry to TENANTS env var first, then):
uv run manage.py create_tenant <slug>

# Fan out pending migrations to all tenants (run after deploy):
uv run manage.py migrate_tenants

# Seed a demo tenant with sample data:
uv run manage.py seed_tenant <slug>
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

The following are intentionally excluded from this scaffold. Add them when the need arises:

- **Background workers (Celery):** Redis broker is ready. Add `celery.py`, Docker Compose worker service, and settings when custom domain verification or email notifications are needed.
- **Additional i18n languages:** Add locale to `frontend/i18n/routing.ts`, create `messages/<locale>.json`, extract strings. English URLs unaffected.
- **Self-serve tenant provisioning:** Requires moving tenant config from env var to DB-backed registry and a signup flow — significant architectural change.
- **OpenAPI spec generation:** Add `drf-spectacular` to auto-generate OpenAPI schema from Django and sync `frontend/types/api.ts`.
