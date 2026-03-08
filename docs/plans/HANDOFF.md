# Handoff: Subagent-Driven Development State

**Date:** 2026-03-08
**Branch:** `claude/multi-tenant-scaffold-01`
**Last commit:** `9bd38e6 fix: linting and formatting`

---

## Execution Status

Two plans are being executed in sequence using **Subagent-Driven Development**:
1. `docs/plans/2026-03-07-multi-tenant-scaffold-implementation.md` — Tasks 1-17 (scaffold)
2. `docs/plans/2026-03-08-frontend-features.md` — Tasks 1-15 (frontend features)

### Scaffold Plan Progress

| Task | Description | Status |
|------|-------------|--------|
| 1 | PROJECT.md and repo structure | ✅ Done |
| 2 | Docker Compose + init_db.sql | ✅ Done |
| 3 | Django backend scaffold (settings, urls, apps) | ✅ Done |
| 4 | safe_schema utility | ✅ Done |
| 5 | TenantMiddleware | ✅ Done |
| 6 | Custom exception handler | ✅ Done |
| 7 | migrate_shared, create_tenant, migrate_tenants commands | ✅ Done |
| 8 | User, OrgUnit, Membership, APIKey models + migrations | ✅ Done |
| 9 | EmailAuthBackend, TenantJWTAuthentication, APIKeyAuthentication, jwt_views | ✅ Done |
| 10 | OrgUnit API endpoints (serializers, views, urls) | ✅ Done |
| 11 | seed_tenant management command | ✅ Done |
| 12 | Full backend test suite pass + ruff lint | ✅ Done |
| **13** | **Next.js frontend setup (create-next-app, Vitest, Dockerfile)** | **⬅ NEXT** |
| 14 | i18n setup with next-intl | ⏳ Pending |
| 15 | API client, types, tenant utilities | ⏳ Pending |
| 16 | Frontend app structure and login pages | ⏳ Pending |
| 17 | Smoke test — Docker Compose up | ⏳ Pending |

### Frontend Features Plan Progress

All 15 tasks: ⏳ Pending (begins after scaffold Task 17)

---

## Key Architecture Notes

### Backend (Django 6 + DRF)

- **Three-tier PostgreSQL:** `public` (locked), `shared` (Django system tables), `{tenant}` (all app tables)
- **Apps:**
  - `core.users` (app_label="users"): User model (UUID PK, email auth)
  - `core.org` (app_label="org"): OrgUnit, Membership, APIKey, Role, IsolationPolicy
  - `core.tenants`: middleware, utils, management commands
- **Auth:**
  - `EmailAuthBackend` — Django backend, email instead of username
  - `TenantJWTAuthentication` — wraps simplejwt, enforces tenant claim in JWT
  - `APIKeyAuthentication` — SHA-256 hashed key lookup, updates last_used_at
- **URLs:** `v1/auth/token/`, `v1/auth/token/refresh/`, `v1/org/units/`, etc.
- **Tenant resolution:** `/t/<slug>/` path prefix (priority) OR Host header → sets `search_path`
- **Test settings:** `config.test_settings` → SQLite in-memory (no Postgres needed for tests)
- **33 tests passing**, zero ruff issues

### Frontend (Next.js 15 — to be set up in Task 13)

- App Router, TypeScript, `--no-tailwind` (Tailwind added in Frontend Task 1)
- Vitest for tests (not Jest)
- Route structure: `app/(tenant)/[locale]/...` with `localePrefix: "as-needed"`
- After scaffold: Frontend Features plan overrides to `localePrefix: "never"` (cookie/Accept-Language locale)
- **Frontend directory is empty** — `create-next-app` has not been run yet

### Key Design Decisions

- Profile photos: local filesystem (`MEDIA_ROOT/avatars/`)
- Org chart: `react-organizational-chart` visual tree
- Invitation: admin creates invite link/email → recipient fills full registration form
- Locale: NOT in URL (`localePrefix: "never"` after Frontend Task 2), NEXT_LOCALE cookie + Accept-Language fallback
- Styling: Tailwind CSS v4 (CSS-based config) + DaisyUI v5 (added in Frontend Task 1)

---

## How to Resume

Start a new Claude Code session in `/Users/wah/dev/template-multi-tier-tenancy` (or clone the repo) on branch `claude/multi-tenant-scaffold-01`, then continue with **Scaffold Task 13**.

Use the **Subagent-Driven Development** skill pattern:
1. Read task spec from the plan file
2. Dispatch implementer subagent
3. Run spec compliance review (superpowers:code-reviewer)
4. Run code quality review (superpowers:code-reviewer)
5. Fix any issues, re-review
6. Mark task complete, move to next

### Task 13 spec (next task to implement):

```
## Task 13: Next.js frontend setup

Files:
- Create: frontend/ (Next.js project)
- Create: frontend/Dockerfile
- Create: frontend/vitest.config.ts

Step 1: Initialize Next.js project
cd frontend
npx create-next-app@latest . --typescript --app --no-tailwind --no-eslint \
  --src-dir=false --import-alias="@/*" --yes

Step 2: Add Vitest
npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom

Step 3: Create frontend/vitest.config.ts (see plan file lines 2192-2206)
Step 4: Create frontend/tests/setup.ts (see plan file lines 2208-2212)
Step 5: Create frontend/Dockerfile (see plan file lines 2214-2227)
Step 6: Update package.json to add "test": "vitest run" script
Step 7: Commit with message "chore: initialise Next.js frontend with TypeScript and Vitest"
```

Full spec at: `docs/plans/2026-03-07-multi-tenant-scaffold-implementation.md` lines 2172-2251

---

## Files of Interest

```
backend/
  config/settings.py          # Django settings (AUTH_USER_MODEL, TENANTS, REST_FRAMEWORK)
  config/urls.py              # URL root (v1/auth/token/, v1/org/)
  config/test_settings.py     # SQLite in-memory test settings
  core/users/models.py        # User(AbstractUser) UUID PK
  core/users/authentication.py # EmailAuthBackend, TenantJWTAuthentication
  core/users/jwt_views.py     # EmailTokenObtainPairView
  core/org/models.py          # OrgUnit, Membership, APIKey, IsolationPolicy, Role
  core/org/authentication.py  # APIKeyAuthentication, APIKeyToken
  core/org/serializers.py     # OrgUnitSerializer, MembershipSerializer, APIKey*
  core/org/views.py           # OrgUnit CRUD + APIKey endpoints
  core/org/urls.py            # URL patterns
  core/tenants/middleware.py  # TenantMiddleware
  core/tenants/utils.py       # safe_schema()
  core/tenants/management/commands/
    migrate_shared.py
    create_tenant.py
    migrate_tenants.py
    seed_tenant.py

docs/plans/
  2026-03-07-multi-tenant-scaffold-implementation.md  # Scaffold plan (17 tasks)
  2026-03-08-frontend-features.md                     # Frontend features plan (15 tasks)
  2026-03-08-frontend-features-design.md              # Design doc for frontend features
  2026-03-07-multi-tenant-scaffold-design.md          # Design doc for scaffold
```
