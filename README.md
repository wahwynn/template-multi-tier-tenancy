# Multi-Tenant Application Scaffold

A full-stack scaffold for multi-tenant applications with hierarchical organisational structure.

- **Backend**: Django 5 + Django REST Framework
- **Frontend**: Next.js 15 (App Router) + TypeScript
- **Database**: PostgreSQL 16 — schema-per-tenant isolation
- **Cache**: Redis 7
- **Auth**: JWT + API key authentication

See the [design document](docs/plans/2026-03-07-multi-tenant-scaffold-design.md) for full architecture decisions.

## Architecture

Each tenant gets an isolated PostgreSQL schema. Tenant configuration lives in the `TENANTS` environment variable (12-factor — no database registry). The middleware resolves the tenant from the request and sets `search_path` accordingly.

The org hierarchy is an unlimited-depth tree (`OrgUnit`, self-referential). Each node has an `isolation_policy` controlling data visibility across parent/child boundaries:

| Policy | Parent sees child | Child sees parent |
|---|---|---|
| `open` | yes | yes |
| `isolated` | no | no |
| `inherit_only` | no | yes |
| `visible_only` | yes | no |

## Quick Start

```bash
# 1. Copy env config
cp .env.example .env
# Edit .env — set DJANGO_SECRET_KEY, JWT_SECRET, and review TENANTS

# 2. Start services
docker compose up --build -d

# 3. Provision tenant schemas
docker compose exec backend uv run manage.py create_tenant acme
docker compose exec backend uv run manage.py create_tenant demo

# 4. Seed demo tenant with sample data
docker compose exec backend uv run manage.py seed_tenant demo
```

- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- Demo tenant login (path prefix): http://localhost:3000/t/demo/login
- Demo tenant dashboard: http://localhost:3000/t/demo/dashboard

### Demo credentials

| Field | Value |
|---|---|
| Email | `admin@demo.local` |
| Password | `demo-password-change-me` |

## Tenant Access

Tenants are resolved from the request in this order:

1. **Path prefix** (local dev): `/t/<slug>/...` — e.g. `http://localhost:3000/t/acme/login`
2. **Domain** (production): `acme.yourdomain.com` — resolved from `TENANTS[].domains`; visit `/login` and the tenant is detected automatically from the hostname

To test domain-based routing locally, add an entry to `/etc/hosts`:

```
127.0.0.1  acme.localhost
```

Then visit `http://acme.localhost:3000/login`.

## Tenant Management

```bash
# Add a new tenant (update TENANTS env var first, then):
uv run manage.py create_tenant <slug>

# Apply pending migrations to all tenant schemas (run at every deploy):
uv run manage.py migrate_tenants

# Seed a tenant with demo data:
uv run manage.py seed_tenant <slug>
```

## API

All endpoints are under `/v1/`. Tenant context is resolved from the request — never passed in the URL or request body.

```
POST   /v1/auth/token/                          obtain JWT
POST   /v1/auth/token/refresh/                  refresh JWT

GET    /v1/org/units/                           list accessible org units
POST   /v1/org/units/                           create org unit
GET    /v1/org/units/{id}/                      get org unit
GET    /v1/org/units/{id}/ancestors/            walk up the tree
GET    /v1/org/units/{id}/descendants/          walk down the tree
GET    /v1/org/units/{id}/members/              list members
POST   /v1/org/units/{id}/members/              add member
GET    /v1/org/units/{id}/api-keys/             list API keys
POST   /v1/org/units/{id}/api-keys/             create API key (key shown once)
DELETE /v1/org/units/{id}/api-keys/{kid}/       revoke API key
```

All error responses follow: `{"error": {"code": "...", "message": "..."}}`

## Running Tests

```bash
# Backend
cd backend && uv run pytest

# Frontend
cd frontend && npm test
```

## Environment Variables

See [.env.example](.env.example) for all required variables.

Key variables:

| Variable | Description |
|---|---|
| `TENANTS` | JSON array of tenant configs (slug, schema, domains) |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `DJANGO_SECRET_KEY` | Django secret key |
| `JWT_SECRET` | JWT signing secret |
| `DEBUG` | Enable Django debug mode (default: false) |
| `NEXT_PUBLIC_API_URL` | Backend base URL seen by the browser |
| `NEXT_PUBLIC_TENANTS` | Same JSON as `TENANTS` — used by `/login` to resolve tenant from hostname (set automatically in docker-compose) |

## Deferred

- **Background workers (Celery)**: Redis broker is ready. Add when async tasks are needed (e.g. custom domain verification, email).
- **Additional i18n languages**: Add locale to `frontend/i18n/routing.ts`, create `messages/<locale>.json`. English URLs unaffected.
- **Self-serve tenant provisioning**: Requires moving tenant config from env var to DB — significant architectural change.
