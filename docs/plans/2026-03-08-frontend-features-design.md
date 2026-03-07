# Frontend Features Design

**Date:** 2026-03-08
**Prerequisite:** `2026-03-07-multi-tenant-scaffold-implementation.md` fully executed

---

## Overview

This document covers the product-layer frontend features built on top of the multi-tenant scaffold. The scaffold provides working JWT auth, tenant routing, and a bare Next.js app. This plan adds polish, user-facing workflows, and the core product pages.

**Features:**
1. Tailwind CSS + DaisyUI (styling system)
2. Login polish + password reset via email
3. User profile management + profile photo upload
4. Org chart (visual tree diagram)
5. User invitation system (email + copyable link)

---

## 1. Styling System: Tailwind CSS + DaisyUI

### Setup

The scaffold plan's Task 13 (`create-next-app`) uses `--no-tailwind`. Change to `--tailwind` to include Tailwind from the start.

After scaffolding:
- `npm install daisyui`
- Add DaisyUI to `tailwind.config.ts` plugins: `require("daisyui")`
- Configure themes in `tailwind.config.ts`:
  ```ts
  daisyui: { themes: ["light", "dark"] }
  ```

### Locale

`next-intl` configured with `localePrefix: "never"` — locale is never in the URL. Middleware detects locale from `NEXT_LOCALE` cookie, falling back to the `Accept-Language` request header. All routes are plain paths: `/login`, `/profile`, `/orgs/[id]/chart`, etc.

### Theme Toggle

- `ThemeProvider` component reads `NEXT_THEME` cookie (or `localStorage`) on mount, applies `data-theme` attribute to `<html>`
- Theme toggle button in the navbar switches between `"light"` and `"dark"` and persists choice to cookie

### Layout

Global layout (`app/layout.tsx`) wraps all pages with:
- `ThemeProvider`
- `NextIntlClientProvider`
- Navbar (logo, nav links, user avatar dropdown, theme toggle)

---

## 2. Login Workflows

### Login Page (`/login`)

Replaces the bare login form from the scaffold with a DaisyUI-styled card:
- `card` container, centered on screen
- `form-control` for each field (email, password)
- `btn btn-primary` submit button with loading spinner (`loading loading-spinner`) while request is in flight
- `alert alert-error` displayed inline on failure (invalid credentials, account inactive)
- Link to `/forgot-password`

### Forgot Password (`/forgot-password`)

- Email input form
- On submit: `POST /api/auth/password-reset/` with `{ email }`
- Always shows success message ("If that email exists, a reset link was sent") regardless of whether the email is registered (prevents user enumeration)

**Backend:**
- `PasswordResetToken` model in the `shared` schema:
  - `id` UUID PK
  - `user` FK to users
  - `token` UUID (unique, indexed)
  - `created_at`, `expires_at` (1 hour from creation)
  - `used_at` (nullable)
- `POST /api/auth/password-reset/` — creates token, sends email via SMTP
- Email contains link: `https://<tenant-domain>/reset-password?token=<uuid>`

**SMTP config** (env vars):
```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=
```

For local dev: `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` (prints to stdout).

### Reset Password (`/reset-password?token=<uuid>`)

- On page load: `GET /api/auth/password-reset/validate/?token=<uuid>` — if invalid/expired, show error and link back to `/forgot-password`
- If valid: show new password + confirm password fields
- On submit: `POST /api/auth/password-reset/confirm/` with `{ token, password }`
- Backend validates token (not expired, not used), sets new password, marks `used_at`
- On success: redirect to `/login` with success toast

---

## 3. User Profile + Profile Photos

### Profile Page (`/profile`)

- Displays: avatar, full name, email (read-only)
- Edit form: full name (inline or modal)
- Avatar section: shows current photo (or default initials avatar), "Upload photo" button

### Photo Upload

- File input accepts JPEG/PNG, client-side validates max 5 MB before upload
- On select: `POST /api/users/me/avatar/` with `multipart/form-data`
- Backend saves file to `MEDIA_ROOT/avatars/<user-uuid>.<ext>` (overwrites previous)
- Returns `{ avatar_url: "/media/avatars/<user-uuid>.<ext>" }`
- Profile page updates avatar display immediately

### Media Serving (Backend)

- `MEDIA_URL = "/media/"`
- `MEDIA_ROOT = BASE_DIR / "media"`
- Django serves `media/` in development via `django.views.static.serve`
- Media endpoint checks tenant JWT before serving — users can only access their own tenant's files

**Note:** Local filesystem storage is appropriate for development and single-server deployments. Migration to object storage (S3/MinIO) can be done later by swapping the Django storage backend.

---

## 4. Org Chart

### Org Chart Page (`/orgs/[id]/chart`)

- Fetches org members: `GET /api/orgs/<id>/members/` (existing endpoint from scaffold)
- Builds tree structure client-side from `reports_to` field on membership records
- Renders using `react-organizational-chart`:
  - Each node: avatar thumbnail + name + role badge (DaisyUI `badge`)
  - Root node = org owner or highest-level member with no `reports_to`
- Responsive: horizontally scrollable container on small screens
- Link from org detail page to chart page

### Package

```bash
npm install react-organizational-chart
```

No backend changes required.

---

## 5. User Invitation System

### Backend

**`InviteToken` model** (in tenant schema, `org` app):
- `id` UUID PK
- `token` UUID (unique, indexed)
- `org` FK to org
- `role` CharField (choices: member, admin)
- `email` EmailField (nullable — if provided, send email; if null, link-only)
- `created_by` FK to user
- `expires_at` (7 days from creation)
- `used_at` (nullable)
- `used_by` FK to user (nullable)

**Endpoints:**
- `POST /api/invites/` — create invite; if `email` provided, send invite email; always return `{ invite_url: "https://<tenant-domain>/invite/<token>" }`
- `GET /api/invites/` — list active (unused, unexpired) invites for the org
- `DELETE /api/invites/<token>/` — revoke invite
- `GET /api/invites/<token>/` — **public** (no auth required); validate token, return `{ org_name, role }` or 404/410
- `POST /api/invites/<token>/register/` — **public**; accepts `{ name, email, password }`; creates user + org membership; marks token used; returns JWT

### Frontend

**Invite Management Page** (`/orgs/[id]/invites`) — admin only:
- Table of active invites: email (or "link only"), role, expiry, "Copy Link" button, "Revoke" button
- "Create Invite" modal:
  - Email field (optional)
  - Role selector (DaisyUI `select`)
  - Submit → shows invite link in a copyable input field after creation

**Invite Registration Page** (`/invite/[token]`):
- On load: `GET /api/invites/<token>/` — if invalid, show "This invite link is invalid or has expired"
- If valid: show org name + role, then registration form:
  - Full name
  - Email (pre-filled if invite had email, editable)
  - Password + confirm password
- On submit: `POST /api/invites/<token>/register/` → on success, store JWT and redirect to `/dashboard`

---

## Data Flow Summary

```
Browser → Next.js (no locale prefix) → API (Django)
                ↓
        Middleware reads NEXT_LOCALE cookie
        (fallback: Accept-Language header)
                ↓
        next-intl loads translations
```

Auth flow (password reset):
```
User → /forgot-password → POST /api/auth/password-reset/
                              ↓
                        Creates PasswordResetToken
                        Sends email via SMTP
                              ↓
User → /reset-password?token=X → POST /api/auth/password-reset/confirm/
                                      ↓
                                Validates token
                                Sets new password
                                Marks token used
                                      ↓
                               Redirect to /login
```

Invite flow:
```
Admin → POST /api/invites/ → sends email (optional) + returns invite_url
                                      ↓
Recipient → /invite/<token> → GET /api/invites/<token>/ (public)
                                      ↓
                            Registration form
                                      ↓
                            POST /api/invites/<token>/register/
                                      ↓
                            User created → JWT returned → /dashboard
```

---

## File Structure (new files)

```
frontend/
  app/
    login/page.tsx
    forgot-password/page.tsx
    reset-password/page.tsx
    profile/page.tsx
    orgs/[id]/chart/page.tsx
    orgs/[id]/invites/page.tsx
    invite/[token]/page.tsx
  components/
    ThemeProvider.tsx
    ThemeToggle.tsx
    Navbar.tsx
    AvatarUpload.tsx
    OrgChart.tsx
    InviteModal.tsx

backend/
  core/
    users/
      models.py           # + PasswordResetToken
      views.py            # + password reset endpoints, avatar upload
      urls.py
    org/
      models.py           # + InviteToken
      views.py            # + invite endpoints
      urls.py
  media/                  # gitignored, created at runtime
```

---

## Open Questions / Future Work

- Profile photo serving in production: swap `FileSystemStorage` for `S3Boto3Storage` (django-storages) when ready to scale
- Email templating: plain-text emails for now; HTML templates can be added later
- Invite link expiry UI: consider showing time remaining in invite table
