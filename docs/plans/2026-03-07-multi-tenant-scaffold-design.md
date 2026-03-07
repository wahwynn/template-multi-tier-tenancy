# Design: Multi-Tenant Application Scaffold

**Date:** 2026-03-07
**Status:** Approved

## Overview

Scaffold a multi-tenant application supporting controlled provisioning of a small number of tenants (companies), each with a hierarchical organisational structure of unlimited depth. The application is full-stack: Django backend, Next.js frontend, PostgreSQL, Redis.

---

## 1. Stack

| Layer | Technology |
|---|---|
| Backend | Django + Django REST Framework |
| Frontend | Next.js (App Router) + TypeScript |
| Database | PostgreSQL 16 |
| Cache / Sessions | Redis 7 |
| Auth | JWT via `djangorestframework-simplejwt` |
| i18n | `next-intl` |
| Containerisation | Docker Compose |
| Python tooling | `uv` |

---

## 2. Tenancy Model

### Strategy: PostgreSQL schema-per-tenant

Each tenant gets its own PostgreSQL schema. All domain tables live inside the tenant schema. There is no shared `public` schema tenant registry — tenant configuration is loaded from an environment variable at startup (12-factor).

### Tenant config (env var)

```bash
TENANTS='[
  {"slug": "acme",  "schema": "acme", "domains": ["acme.yoursaas.com", "app.acme.com"], "demo": false},
  {"slug": "demo",  "schema": "demo", "domains": [], "demo": true}
]'
```

### Tenant resolution (priority order)

1. Path prefix: `/t/<slug>/` — used for local development
2. `Host` header lookup against `domains` list — covers both subdomains and custom domains

The `TenantMiddleware` reads `settings.TENANTS` (no DB query), sets `search_path = <schema>, public` on the connection for the duration of the request.

### Tenant lifecycle (management commands)

```bash
# Provision a new tenant schema and run migrations into it
uv run manage.py create_tenant <slug>

# Fan out pending migrations across all tenant schemas (run at deploy)
uv run manage.py migrate_tenants

# Seed a demo tenant with sample fixture data
uv run manage.py seed_tenant <slug>
```

Migration fan-out is safe to re-run — each schema owns its `django_migrations` table and skips already-applied migrations. Failed schemas are reported clearly; re-running resumes from the failure point.

### No django-tenants dependency

The schema isolation and middleware are custom (~150 lines total). This avoids a library dependency and keeps the tenant resolution fully transparent. Redis is already available as a Celery broker when background tasks are needed in future.

---

## 3. Data Model

All models live inside each tenant's schema.

### OrgUnit (self-referential tree)

```
OrgUnit
  id                uuid, PK
  name              str
  slug              str, unique within parent scope
  parent_id         FK → OrgUnit (nullable, root nodes have no parent)
  node_type         str  (free label: "org", "department", "team", "franchise", etc.)
  isolation_policy  enum, default "open"
```

**`isolation_policy` values:**

| Value | Parent sees in | Child sees parent | Example |
|---|---|---|---|
| `open` | yes | yes | Corp HQ <-> owned subsidiary |
| `isolated` | no | no | Legal, Accounting |
| `inherit_only` | no | yes | Private team that reads company-wide announcements |
| `visible_only` | yes | no | Corp-run franchise — corp has oversight, franchise is data-blind to corp |

Tree traversal uses PostgreSQL recursive CTEs. At query time, the system walks the tree from the user's node(s), respecting `isolation_policy` at each boundary to determine the full scope of accessible nodes.

### Membership

```
Membership
  id          uuid, PK
  user_id     FK → User
  org_unit_id FK → OrgUnit
  role        enum("owner" | "admin" | "member" | "viewer")
  UNIQUE(user_id, org_unit_id)
```

- Membership is explicit at every level — no auto-propagation when added to a child node
- A user belongs to at most one root OrgUnit per tenant
- Roles are assigned independently per OrgUnit — a user can be `admin` in one unit and `viewer` in another

### APIKey

```
APIKey
  id                uuid, PK
  name              str
  prefix            str  (first 8 chars, shown in listings)
  hashed_key        str  (SHA-256, never stored plaintext)
  org_unit_id       FK → OrgUnit
  role              enum("owner" | "admin" | "member" | "viewer")
  created_by_user_id FK → User  (audit trail only)
  expires_at        datetime (nullable)
  last_used_at      datetime (nullable)
```

Keys belong to an OrgUnit, not a user. Permissions are explicit on the key (not inherited from the creator). Full key shown exactly once at creation, never retrievable again. Key access respects the same `isolation_policy` tree-walk as user access.

---

## 4. API Design

**Base URL:** `/v1/`

All responses use a consistent error shape:
```json
{"error": {"code": "...", "message": "..."}}
```

Tenant context is implicit — resolved from the request by middleware, never in the URL or request body. All list endpoints use cursor-based pagination.

### Authentication

```
POST   /v1/auth/token/               obtain JWT (email + password)
POST   /v1/auth/token/refresh/       refresh JWT
```

JWT contains `user_id` and `tenant_slug`. Refresh tokens stored in Redis with expiry.

**API key authentication:** `Authorization: Bearer <api-key>` — same header as JWT. Auth backend checks JWT format first; otherwise hashes the value and looks up prefix + hash in the `APIKey` table.

### OrgUnit hierarchy

```
GET    /v1/org/units/                     list units accessible to caller
POST   /v1/org/units/                     create unit
GET    /v1/org/units/{id}/                get unit + immediate children
PATCH  /v1/org/units/{id}/                update unit
DELETE /v1/org/units/{id}/                delete unit (must be a leaf node)
GET    /v1/org/units/{id}/ancestors/      walk up the tree
GET    /v1/org/units/{id}/descendants/    walk down the tree
```

### Membership

```
GET    /v1/org/units/{id}/members/           list members
POST   /v1/org/units/{id}/members/           add member + role
PATCH  /v1/org/units/{id}/members/{uid}/     change role
DELETE /v1/org/units/{id}/members/{uid}/     remove member
```

### API Keys

```
GET    /v1/org/units/{id}/api-keys/          list keys (prefix + name only, never full key)
POST   /v1/org/units/{id}/api-keys/          create key (full key shown once in response)
DELETE /v1/org/units/{id}/api-keys/{kid}/    revoke key
```

### Users

```
GET    /v1/users/me/                         current user + their memberships
```

---

## 5. Frontend Structure

```
frontend/
  app/
    (auth)/
      login/
      logout/
    (tenant)/
      [locale]/              mandatory — locale prefix applied to all tenant routes
        layout.tsx           resolves tenant context, injects into providers
        dashboard/
        org/
          units/
          units/[id]/
          units/[id]/members/
        settings/
        api-keys/
  components/
    ui/                      primitives (button, input, etc.)
    org/                     org hierarchy components
    auth/                    login forms, token handling
  lib/
    api.ts                   typed API client (wraps fetch, injects JWT, auto-refresh)
    tenant.ts                tenant context resolution
    auth.ts                  token storage, refresh logic
    i18n.ts                  locale detection + next-intl config
  messages/
    en.json                  English translations (only language at launch)
  types/
    api.ts                   TypeScript interfaces mirroring backend response shapes
```

### Key frontend decisions

- JWT stored in `httpOnly` cookie — not `localStorage`, avoids XSS exposure
- All backend calls go through `lib/api.ts` — consistent error handling, automatic token refresh
- Frontend `types/api.ts` kept in sync with backend via OpenAPI spec generated from Django
- i18n uses `next-intl` with `localePrefix: "as-needed"` — English URLs have no prefix (`/dashboard`), other locales are prefixed (`/fr/dashboard`). Adding a language later does not break English URLs.
- Translation files start English-only. String extraction deferred until a second language is needed.

---

## 6. Local Development

### Docker Compose services

```
backend    Django, port 8000
frontend   Next.js, port 3000
db         PostgreSQL 16
redis      Redis 7
```

### Local tenant access

Path prefix is the local dev default (no wildcard DNS needed):

```
http://localhost:3000/t/acme/dashboard
http://localhost:3000/t/demo/dashboard
```

### Environment variables (`.env`)

```bash
TENANTS='[{"slug":"acme","schema":"acme","domains":["acme.localhost"]},{"slug":"demo","schema":"demo","domains":[],"demo":true}]'
DATABASE_URL=postgres://user:pass@db:5432/app
REDIS_URL=redis://redis:6379/0
JWT_SECRET=...
JWT_ACCESS_TOKEN_EXPIRY=3600
JWT_REFRESH_TOKEN_EXPIRY=86400
```

---

## 7. Testing Strategy

| Layer | Tool | Notes |
|---|---|---|
| Backend unit | pytest | Services/models in isolation, fixture creates fresh tenant schema per session |
| Backend API | pytest + DRF test client | Full request cycle, tenant set via `/t/<slug>/` path prefix |
| Frontend unit | Vitest | Components in isolation, mock API client |
| Frontend e2e | Playwright | Full stack via Docker Compose, `demo` tenant seeded with fixture data |

- Backend tests get a fresh tenant schema via pytest fixture — no cross-test contamination
- No DB mocking in integration tests — real PostgreSQL, fast enough with schemas
- API key auth path tested separately from JWT path
- Key scoping tested: key on node X cannot access node Y (isolation enforced)
- Expired keys tested: return `401`

---

## 8. Deferred Decisions

### Background workers (Celery)

No designed feature currently requires async task execution. Redis is already in the stack and available as a Celery broker. The natural point to add it is when custom domain verification or email notifications are built.

To add later (contained change):
- One Docker Compose worker service
- One `celery.py` config file
- One Django settings addition

### Additional languages (i18n)

`next-intl` scaffolding is in place with `localePrefix: "as-needed"`. To add a language: add the locale to `i18n.ts`, create `messages/<locale>.json`, extract strings. English URLs are unaffected.

### Self-serve tenant provisioning

Current model is controlled provisioning (ops runs `create_tenant`). Self-serve would require moving tenant config from env var to a DB-backed registry and adding a signup flow. This is a significant architectural change — decide before building it.
