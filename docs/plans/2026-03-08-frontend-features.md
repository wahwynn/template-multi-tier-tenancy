# Frontend Features Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Tailwind CSS + DaisyUI styling, polished login with password reset, user profile management with photo upload, org chart, and user invitation system to the multi-tenant Next.js app.

**Architecture:** Separate supplementary plan that picks up after `2026-03-07-multi-tenant-scaffold-implementation.md` completes. Backend adds `PasswordResetToken`, `InviteToken`, `User.avatar`, and `Membership.reports_to`. Frontend adds new pages and polished components. All routes are locale-prefix-free (`localePrefix: "never"`).

**Tech Stack:** Next.js 15 (App Router), TypeScript, Tailwind CSS v4, DaisyUI v5, react-organizational-chart, Vitest, Django 6, DRF, pytest

**Design doc:** `docs/plans/2026-03-08-frontend-features-design.md`

---

## Prerequisites

- `2026-03-07-multi-tenant-scaffold-implementation.md` fully executed
- Docker services running (`docker compose up -d`)
- Working directory: `frontend/` for frontend steps, `backend/` for backend steps

---

## Task 1: Install Tailwind CSS + DaisyUI

**Files:**
- Create: `frontend/postcss.config.mjs`
- Modify: `frontend/app/globals.css`
- Modify: `frontend/package.json` (via npm install)

**Context:** The scaffold used `--no-tailwind`. Tailwind v4 uses CSS-based config (no `tailwind.config.ts`). DaisyUI v5 is the plugin for Tailwind v4.

**Step 1: Install packages**

```bash
cd frontend
npm install tailwindcss @tailwindcss/postcss postcss daisyui
```

**Step 2: Create postcss.config.mjs**

```js
export default {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};
```

**Step 3: Replace app/globals.css**

```css
@import "tailwindcss";

@plugin "daisyui" {
  themes: light --default, dark;
}
```

**Step 4: Verify Tailwind loads**

Start dev server and check that a test element with `class="btn btn-primary"` renders with DaisyUI styles:

```bash
npm run dev
```

Open `http://localhost:3000`. No visual errors expected (scaffold has minimal HTML at this point).

**Step 5: Commit**

```bash
cd ..
git add frontend/postcss.config.mjs frontend/app/globals.css frontend/package.json frontend/package-lock.json
git commit -m "feat: add Tailwind CSS v4 + DaisyUI v5"
```

---

## Task 2: Update i18n routing to localePrefix: "never"

**Files:**
- Modify: `frontend/i18n/routing.ts`
- Modify: `frontend/messages/en.json`

**Context:** `localePrefix: "never"` removes locale from visible URLs. The `[locale]` segment remains in the filesystem; next-intl middleware rewrites internally. Locale is detected from the `NEXT_LOCALE` cookie (set by next-intl's built-in logic), falling back to `Accept-Language`. This is automatic when `localePrefix: "never"` is used.

**Step 1: Update routing.ts**

Replace `frontend/i18n/routing.ts` content:

```typescript
import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["en"],
  defaultLocale: "en",
  localePrefix: "never",
});
```

**Step 2: Expand messages/en.json with new translation keys**

Replace `frontend/messages/en.json`:

```json
{
  "auth": {
    "login": "Sign in",
    "email": "Email",
    "password": "Password",
    "submit": "Sign in",
    "forgotPassword": "Forgot password?",
    "forgotPasswordTitle": "Reset your password",
    "forgotPasswordDescription": "Enter your email and we'll send a reset link.",
    "sendResetLink": "Send reset link",
    "resetPasswordTitle": "Set new password",
    "newPassword": "New password",
    "confirmPassword": "Confirm password",
    "resetPassword": "Reset password",
    "resetSuccess": "Password reset successfully. Please sign in.",
    "invalidToken": "This reset link is invalid or has expired.",
    "checkEmail": "If that email exists, a reset link was sent."
  },
  "nav": {
    "dashboard": "Dashboard",
    "profile": "Profile",
    "orgs": "Orgs",
    "signOut": "Sign out"
  },
  "profile": {
    "title": "Profile",
    "fullName": "Full name",
    "email": "Email",
    "avatar": "Profile photo",
    "uploadPhoto": "Upload photo",
    "saveChanges": "Save changes",
    "saved": "Changes saved."
  },
  "org": {
    "units": "Org Units",
    "dashboard": "Dashboard",
    "chart": "Org Chart",
    "invites": "Invitations"
  },
  "invites": {
    "createInvite": "Create invitation",
    "emailOptional": "Email (optional)",
    "role": "Role",
    "send": "Send invitation",
    "copyLink": "Copy link",
    "copied": "Copied!",
    "revoke": "Revoke",
    "linkOnly": "Link only",
    "expiresAt": "Expires",
    "noInvites": "No active invitations.",
    "joinTitle": "You've been invited",
    "joinOrg": "Join {org} as {role}",
    "fullName": "Full name",
    "createAccount": "Create account",
    "invalidInvite": "This invitation link is invalid or has expired."
  }
}
```

**Step 3: Commit**

```bash
git add frontend/i18n/routing.ts frontend/messages/en.json
git commit -m "feat: switch next-intl to localePrefix never (cookie/Accept-Language locale detection)"
```

---

## Task 3: ThemeProvider, Navbar, and global layout

**Files:**
- Create: `frontend/components/ThemeProvider.tsx`
- Create: `frontend/components/ThemeToggle.tsx`
- Create: `frontend/components/Navbar.tsx`
- Modify: `frontend/app/(tenant)/[locale]/layout.tsx`
- Create: `frontend/tests/components/ThemeProvider.test.tsx`

**Step 1: Write the failing test**

Create `frontend/tests/components/ThemeProvider.test.tsx`:

```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ThemeProvider, { useTheme } from "@/components/ThemeProvider";

function ThemeConsumer() {
  const { theme, toggle } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <button onClick={toggle}>Toggle</button>
    </div>
  );
}

describe("ThemeProvider", () => {
  it("defaults to light theme", () => {
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );
    expect(screen.getByTestId("theme").textContent).toBe("light");
  });

  it("toggles theme on button click", () => {
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );
    fireEvent.click(screen.getByText("Toggle"));
    expect(screen.getByTestId("theme").textContent).toBe("dark");
  });
});
```

**Step 2: Run test to verify it fails**

```bash
cd frontend && npm test -- --reporter=verbose tests/components/ThemeProvider.test.tsx
```

Expected: FAIL with "Cannot find module '@/components/ThemeProvider'"

**Step 3: Create ThemeProvider.tsx**

Create `frontend/components/ThemeProvider.tsx`:

```typescript
"use client";

import { createContext, useContext, useEffect, useState } from "react";

type Theme = "light" | "dark";

interface ThemeContextValue {
  theme: Theme;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: "light",
  toggle: () => {},
});

export function useTheme() {
  return useContext(ThemeContext);
}

function getStoredTheme(): Theme {
  if (typeof document === "undefined") return "light";
  const cookie = document.cookie
    .split("; ")
    .find((row) => row.startsWith("NEXT_THEME="))
    ?.split("=")[1];
  if (cookie === "dark" || cookie === "light") return cookie;
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export default function ThemeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const initial = getStoredTheme();
    setTheme(initial);
    document.documentElement.setAttribute("data-theme", initial);
  }, []);

  function toggle() {
    const next: Theme = theme === "light" ? "dark" : "light";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    document.cookie = `NEXT_THEME=${next}; path=/; max-age=31536000; SameSite=Lax`;
  }

  return (
    <ThemeContext.Provider value={{ theme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}
```

**Step 4: Create ThemeToggle.tsx**

Create `frontend/components/ThemeToggle.tsx`:

```typescript
"use client";

import { useTheme } from "./ThemeProvider";

export default function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      className="btn btn-ghost btn-circle"
      onClick={toggle}
      aria-label="Toggle theme"
    >
      {theme === "light" ? "🌙" : "☀️"}
    </button>
  );
}
```

**Step 5: Create Navbar.tsx**

Create `frontend/components/Navbar.tsx`:

```typescript
import ThemeToggle from "./ThemeToggle";

interface Props {
  userInitials?: string;
}

export default function Navbar({ userInitials = "U" }: Props) {
  return (
    <div className="navbar bg-base-100 shadow-sm">
      <div className="flex-1">
        <a href="/" className="btn btn-ghost text-xl font-bold">
          App
        </a>
      </div>
      <div className="flex-none gap-2">
        <ThemeToggle />
        <div className="dropdown dropdown-end">
          <div
            tabIndex={0}
            role="button"
            className="btn btn-ghost btn-circle avatar placeholder"
          >
            <div className="bg-neutral text-neutral-content rounded-full w-10 flex items-center justify-center">
              <span className="text-sm font-bold">{userInitials}</span>
            </div>
          </div>
          <ul
            tabIndex={0}
            className="menu menu-sm dropdown-content bg-base-100 rounded-box z-10 mt-3 w-52 p-2 shadow"
          >
            <li>
              <a href="/profile">Profile</a>
            </li>
            <li>
              <a href="/login">Sign out</a>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
```

**Step 6: Update layout.tsx to include ThemeProvider and Navbar**

Replace `frontend/app/(tenant)/[locale]/layout.tsx`:

```typescript
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { ReactNode } from "react";
import Navbar from "@/components/Navbar";
import ThemeProvider from "@/components/ThemeProvider";
import "@/app/globals.css";

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
        <ThemeProvider>
          <NextIntlClientProvider messages={messages}>
            <Navbar />
            <main>{children}</main>
          </NextIntlClientProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
```

**Step 7: Run test to verify it passes**

```bash
npm test -- --reporter=verbose tests/components/ThemeProvider.test.tsx
```

Expected: PASS (2 tests)

**Step 8: Commit**

```bash
cd ..
git add frontend/components/ frontend/app/ frontend/tests/
git commit -m "feat: add ThemeProvider, ThemeToggle, Navbar, and styled global layout"
```

---

## Task 4: Polish login page with DaisyUI

**Files:**
- Modify: `frontend/components/LoginForm.tsx`
- Create: `frontend/tests/components/LoginForm.test.tsx`

**Context:** The scaffold created a bare HTML login form. Replace it with a DaisyUI card layout with loading state and error display. Keep the same props and callback logic.

**Step 1: Write the failing test**

Create `frontend/tests/components/LoginForm.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import LoginForm from "@/components/LoginForm";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  obtainToken: vi.fn().mockRejectedValue(new Error("Invalid credentials")),
}));

describe("LoginForm", () => {
  it("renders email and password fields", () => {
    render(<LoginForm slug="acme" />);
    expect(screen.getByLabelText(/email/i)).toBeTruthy();
    expect(screen.getByLabelText(/password/i)).toBeTruthy();
  });

  it("shows error message on failed login", async () => {
    render(<LoginForm slug="acme" />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "a@b.com" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeTruthy();
    });
  });

  it("has a link to forgot password", () => {
    render(<LoginForm slug="acme" />);
    expect(screen.getByText(/forgot password/i)).toBeTruthy();
  });
});
```

**Step 2: Run test to verify it fails**

```bash
cd frontend && npm test -- --reporter=verbose tests/components/LoginForm.test.tsx
```

Expected: FAIL (missing DaisyUI classes, missing forgot password link)

**Step 3: Replace LoginForm.tsx**

Replace `frontend/components/LoginForm.tsx`:

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
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { access } = await obtainToken(slug, email, password);
      document.cookie = `access_token=${access}; path=/; SameSite=Lax`;
      router.push(`/t/${slug}/dashboard`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-base-200">
      <div className="card bg-base-100 shadow-xl w-full max-w-sm">
        <div className="card-body">
          <h1 className="card-title text-2xl mb-2">Sign in</h1>

          {error && (
            <div role="alert" className="alert alert-error text-sm">
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <div className="form-control">
              <label className="label" htmlFor="email">
                <span className="label-text">Email</span>
              </label>
              <input
                id="email"
                type="email"
                className="input input-bordered"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>

            <div className="form-control">
              <label className="label" htmlFor="password">
                <span className="label-text">Password</span>
              </label>
              <input
                id="password"
                type="password"
                className="input input-bordered"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
              <label className="label">
                <a
                  href="/forgot-password"
                  className="label-text-alt link link-hover"
                >
                  Forgot password?
                </a>
              </label>
            </div>

            <button
              type="submit"
              className="btn btn-primary mt-2"
              disabled={loading}
            >
              {loading && (
                <span className="loading loading-spinner loading-sm" />
              )}
              Sign in
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
```

**Step 4: Run test to verify it passes**

```bash
npm test -- --reporter=verbose tests/components/LoginForm.test.tsx
```

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
cd ..
git add frontend/components/LoginForm.tsx frontend/tests/components/LoginForm.test.tsx
git commit -m "feat: restyle login form with DaisyUI card, loading state, and forgot-password link"
```

---

## Task 5: Backend — PasswordResetToken model

**Files:**
- Modify: `backend/core/users/models.py`
- Create: `backend/core/users/migrations/000N_add_password_reset_token.py` (auto-generated)
- Create: `backend/tests/users/test_password_reset_token.py`

**Context:** `PasswordResetToken` lives in the `users` app (tenant schema). Each tenant has its own token table. Reset links include the tenant domain so tenant context is always available.

**Step 1: Write the failing test**

Create `backend/tests/users/test_password_reset_token.py`:

```python
"""Tests for PasswordResetToken model."""

import uuid
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from core.users.models import PasswordResetToken, User


class PasswordResetTokenTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice", email="alice@example.com", password="pass"
        )

    def _make_token(self, expires_delta: timedelta = timedelta(hours=1)) -> PasswordResetToken:
        return PasswordResetToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + expires_delta,
        )

    def test_token_is_valid_when_fresh(self):
        token = self._make_token()
        assert token.is_valid() is True

    def test_token_is_invalid_when_expired(self):
        token = self._make_token(expires_delta=timedelta(hours=-1))
        assert token.is_valid() is False

    def test_token_is_invalid_when_used(self):
        token = self._make_token()
        token.used_at = timezone.now()
        token.save()
        assert token.is_valid() is False

    def test_token_uuid_is_auto_generated(self):
        token = self._make_token()
        assert isinstance(token.token, uuid.UUID)

    def test_table_name(self):
        assert PasswordResetToken._meta.db_table == "password_reset_tokens"
```

**Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/users/test_password_reset_token.py -v
```

Expected: FAIL with "cannot import name 'PasswordResetToken'"

**Step 3: Add PasswordResetToken to models.py**

Open `backend/core/users/models.py` and append after the existing `User` model:

```python
class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "users"
        db_table = "password_reset_tokens"

    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()
```

Make sure `from django.utils import timezone` is imported at the top of `models.py`.

**Step 4: Generate and apply migration**

```bash
uv run python manage.py makemigrations users --name add_password_reset_token
uv run python manage.py migrate_tenants
```

Expected: migration file created, applied to all tenant schemas.

**Step 5: Run test to verify it passes**

```bash
uv run pytest tests/users/test_password_reset_token.py -v
```

Expected: PASS (5 tests)

**Step 6: Commit**

```bash
cd ..
git add backend/core/users/models.py backend/core/users/migrations/ backend/tests/users/test_password_reset_token.py
git commit -m "feat: add PasswordResetToken model to users app"
```

---

## Task 6: Backend — password reset endpoints

**Files:**
- Create: `backend/core/users/password_reset_views.py`
- Modify: `backend/config/urls.py`
- Create: `backend/tests/users/test_password_reset_api.py`

**Context:** Three endpoints, all `AllowAny`. Request endpoint never reveals whether an email exists (prevents user enumeration). Validate endpoint lets the frontend check a token before showing the form. Confirm endpoint sets the new password and invalidates the token. Email sending uses Django's email backend (console backend in dev, SMTP in prod via env vars).

**Step 1: Write the failing tests**

Create `backend/tests/users/test_password_reset_api.py`:

```python
"""Tests for password reset API endpoints."""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from core.users.models import PasswordResetToken, User


class PasswordResetRequestTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="bob", email="bob@example.com", password="oldpass"
        )

    @patch("core.users.password_reset_views.send_mail")
    def test_known_email_creates_token_and_sends_email(self, mock_mail):
        response = self.client.post(
            "/v1/auth/password-reset/", {"email": "bob@example.com"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert PasswordResetToken.objects.filter(user=self.user).exists()
        assert mock_mail.called

    @patch("core.users.password_reset_views.send_mail")
    def test_unknown_email_returns_200_without_creating_token(self, mock_mail):
        response = self.client.post(
            "/v1/auth/password-reset/", {"email": "nobody@example.com"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert not mock_mail.called


class PasswordResetValidateTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="carol", email="carol@example.com", password="pass"
        )

    def _make_token(self, **kwargs) -> PasswordResetToken:
        return PasswordResetToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(hours=1),
            **kwargs,
        )

    def test_valid_token_returns_valid_true(self):
        token = self._make_token()
        response = self.client.get(
            f"/v1/auth/password-reset/validate/?token={token.token}"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["valid"] is True

    def test_expired_token_returns_410(self):
        token = PasswordResetToken.objects.create(
            user=self.user,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        response = self.client.get(
            f"/v1/auth/password-reset/validate/?token={token.token}"
        )
        assert response.status_code == status.HTTP_410_GONE

    def test_invalid_uuid_returns_404(self):
        response = self.client.get(
            "/v1/auth/password-reset/validate/?token=not-a-uuid"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class PasswordResetConfirmTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="dave", email="dave@example.com", password="oldpass"
        )

    def _make_token(self) -> PasswordResetToken:
        return PasswordResetToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(hours=1),
        )

    def test_confirm_sets_new_password(self):
        token = self._make_token()
        response = self.client.post(
            "/v1/auth/password-reset/confirm/",
            {"token": str(token.token), "password": "newpass123"},
        )
        assert response.status_code == status.HTTP_200_OK
        self.user.refresh_from_db()
        assert self.user.check_password("newpass123")

    def test_confirm_marks_token_used(self):
        token = self._make_token()
        self.client.post(
            "/v1/auth/password-reset/confirm/",
            {"token": str(token.token), "password": "newpass123"},
        )
        token.refresh_from_db()
        assert token.used_at is not None

    def test_confirm_rejects_used_token(self):
        token = self._make_token()
        token.used_at = timezone.now()
        token.save()
        response = self.client.post(
            "/v1/auth/password-reset/confirm/",
            {"token": str(token.token), "password": "newpass123"},
        )
        assert response.status_code == status.HTTP_410_GONE

    def test_confirm_rejects_short_password(self):
        token = self._make_token()
        response = self.client.post(
            "/v1/auth/password-reset/confirm/",
            {"token": str(token.token), "password": "short"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
```

**Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/users/test_password_reset_api.py -v
```

Expected: FAIL with "404 Not Found" (endpoints don't exist yet)

**Step 3: Create password_reset_views.py**

Create `backend/core/users/password_reset_views.py`:

```python
"""Password reset API endpoints."""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.users.models import PasswordResetToken, User


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        email = request.data.get("email", "")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "If that email exists, a reset link was sent."}
            )

        token = PasswordResetToken.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        reset_url = (
            f"{request.scheme}://{request.get_host()}"
            f"/reset-password?token={token.token}"
        )
        send_mail(
            subject="Reset your password",
            message=(
                f"Click the link to reset your password:\n\n{reset_url}\n\n"
                "This link expires in 1 hour."
            ),
            from_email=None,  # Uses DEFAULT_FROM_EMAIL from settings
            recipient_list=[user.email],
        )
        return Response({"detail": "If that email exists, a reset link was sent."})


class PasswordResetValidateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        token_str = request.query_params.get("token", "")
        try:
            token_uuid = uuid.UUID(token_str)
            token = PasswordResetToken.objects.get(token=token_uuid)
        except (ValueError, PasswordResetToken.DoesNotExist):
            return Response(
                {"valid": False, "detail": "Invalid token."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not token.is_valid():
            return Response(
                {"valid": False, "detail": "Token expired or already used."},
                status=status.HTTP_410_GONE,
            )
        return Response({"valid": True})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        token_str = request.data.get("token", "")
        password = request.data.get("password", "")

        if len(password) < 8:
            return Response(
                {"detail": "Password must be at least 8 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token_uuid = uuid.UUID(token_str)
            token = PasswordResetToken.objects.get(token=token_uuid)
        except (ValueError, PasswordResetToken.DoesNotExist):
            return Response(
                {"detail": "Invalid token."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not token.is_valid():
            return Response(
                {"detail": "Token expired or already used."},
                status=status.HTTP_410_GONE,
            )

        token.user.set_password(password)
        token.user.save()
        token.used_at = timezone.now()
        token.save()

        return Response({"detail": "Password reset successful."})
```

**Step 4: Register URL routes**

Open `backend/config/urls.py` and add the three new paths to `urlpatterns`:

```python
from core.users.password_reset_views import (
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetValidateView,
)

# Add to urlpatterns:
path("v1/auth/password-reset/", PasswordResetRequestView.as_view(), name="password-reset-request"),
path("v1/auth/password-reset/validate/", PasswordResetValidateView.as_view(), name="password-reset-validate"),
path("v1/auth/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
```

**Step 5: Add email settings to .env.example**

Open `.env.example` and append:

```
# Email (use console backend in dev; set SMTP vars for production)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@example.com
```

Add the corresponding settings to `backend/config/settings.py`:

```python
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")
```

(`env` is the `environ.Env()` instance already in settings.py from the scaffold.)

**Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/users/test_password_reset_api.py -v
```

Expected: PASS (8 tests)

**Step 7: Commit**

```bash
cd ..
git add backend/core/users/password_reset_views.py backend/config/urls.py backend/config/settings.py .env.example
git commit -m "feat: add password reset endpoints (request, validate, confirm) with SMTP email"
```

---

## Task 7: Frontend — forgot-password and reset-password pages

**Files:**
- Create: `frontend/components/ForgotPasswordForm.tsx`
- Create: `frontend/components/ResetPasswordForm.tsx`
- Create: `frontend/app/(tenant)/[locale]/forgot-password/page.tsx`
- Create: `frontend/app/(tenant)/[locale]/reset-password/page.tsx`
- Modify: `frontend/lib/api.ts`
- Create: `frontend/tests/components/ForgotPasswordForm.test.tsx`

**Step 1: Add API functions to lib/api.ts**

Open `frontend/lib/api.ts` and add these functions after the existing exports:

```typescript
export async function requestPasswordReset(
  slug: string,
  email: string
): Promise<void> {
  await request(`/t/${slug}/v1/auth/password-reset/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

export async function validateResetToken(
  slug: string,
  token: string
): Promise<boolean> {
  const res = await request(
    `/t/${slug}/v1/auth/password-reset/validate/?token=${token}`
  );
  return (res as { valid: boolean }).valid;
}

export async function confirmPasswordReset(
  slug: string,
  token: string,
  password: string
): Promise<void> {
  await request(`/t/${slug}/v1/auth/password-reset/confirm/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, password }),
  });
}
```

**Step 2: Write the failing test**

Create `frontend/tests/components/ForgotPasswordForm.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ForgotPasswordForm from "@/components/ForgotPasswordForm";

vi.mock("@/lib/api", () => ({
  requestPasswordReset: vi.fn().mockResolvedValue(undefined),
}));

describe("ForgotPasswordForm", () => {
  it("renders email input", () => {
    render(<ForgotPasswordForm slug="acme" />);
    expect(screen.getByLabelText(/email/i)).toBeTruthy();
  });

  it("shows success message after submit", async () => {
    render(<ForgotPasswordForm slug="acme" />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "user@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send reset link/i }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeTruthy();
    });
  });
});
```

**Step 3: Run test to verify it fails**

```bash
cd frontend && npm test -- --reporter=verbose tests/components/ForgotPasswordForm.test.tsx
```

Expected: FAIL with "Cannot find module"

**Step 4: Create ForgotPasswordForm.tsx**

Create `frontend/components/ForgotPasswordForm.tsx`:

```typescript
"use client";

import { useState } from "react";
import { requestPasswordReset } from "@/lib/api";

interface Props {
  slug: string;
}

export default function ForgotPasswordForm({ slug }: Props) {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await requestPasswordReset(slug, email);
    } finally {
      setLoading(false);
      setSubmitted(true);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-base-200">
      <div className="card bg-base-100 shadow-xl w-full max-w-sm">
        <div className="card-body">
          <h1 className="card-title text-2xl mb-1">Reset your password</h1>
          <p className="text-sm text-base-content/70 mb-3">
            Enter your email and we&apos;ll send a reset link.
          </p>

          {submitted ? (
            <div role="alert" className="alert alert-success">
              <span>If that email exists, a reset link was sent.</span>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-3">
              <div className="form-control">
                <label className="label" htmlFor="email">
                  <span className="label-text">Email</span>
                </label>
                <input
                  id="email"
                  type="email"
                  className="input input-bordered"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>
              <button
                type="submit"
                className="btn btn-primary mt-2"
                disabled={loading}
              >
                {loading && (
                  <span className="loading loading-spinner loading-sm" />
                )}
                Send reset link
              </button>
            </form>
          )}

          <div className="mt-4 text-center text-sm">
            <a href="/login" className="link link-hover">
              Back to sign in
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
```

**Step 5: Create ResetPasswordForm.tsx**

Create `frontend/components/ResetPasswordForm.tsx`:

```typescript
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { confirmPasswordReset } from "@/lib/api";

interface Props {
  slug: string;
  token: string;
}

export default function ResetPasswordForm({ slug, token }: Props) {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await confirmPasswordReset(slug, token, password);
      router.push("/login?reset=1");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Reset failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-base-200">
      <div className="card bg-base-100 shadow-xl w-full max-w-sm">
        <div className="card-body">
          <h1 className="card-title text-2xl mb-2">Set new password</h1>

          {error && (
            <div role="alert" className="alert alert-error text-sm">
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <div className="form-control">
              <label className="label" htmlFor="password">
                <span className="label-text">New password</span>
              </label>
              <input
                id="password"
                type="password"
                className="input input-bordered"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
              />
            </div>

            <div className="form-control">
              <label className="label" htmlFor="confirm">
                <span className="label-text">Confirm password</span>
              </label>
              <input
                id="confirm"
                type="password"
                className="input input-bordered"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary mt-2"
              disabled={loading}
            >
              {loading && (
                <span className="loading loading-spinner loading-sm" />
              )}
              Reset password
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
```

**Step 6: Create the page routes**

Create `frontend/app/(tenant)/[locale]/forgot-password/page.tsx`:

```typescript
import { headers } from "next/headers";
import { notFound } from "next/navigation";
import ForgotPasswordForm from "@/components/ForgotPasswordForm";
import { getTenantSlugFromHostname } from "@/lib/tenant";

export default async function ForgotPasswordPage() {
  const host = (await headers()).get("host") ?? "";
  const slug = getTenantSlugFromHostname(host) ?? "demo";
  if (!slug) notFound();
  return <ForgotPasswordForm slug={slug} />;
}
```

Create `frontend/app/(tenant)/[locale]/reset-password/page.tsx`:

```typescript
import { headers } from "next/headers";
import { notFound, redirect } from "next/navigation";
import ResetPasswordForm from "@/components/ResetPasswordForm";
import { getTenantSlugFromHostname } from "@/lib/tenant";
import { validateResetToken } from "@/lib/api";

interface Props {
  searchParams: Promise<{ token?: string }>;
}

export default async function ResetPasswordPage({ searchParams }: Props) {
  const host = (await headers()).get("host") ?? "";
  const slug = getTenantSlugFromHostname(host) ?? "demo";
  if (!slug) notFound();

  const { token } = await searchParams;
  if (!token) redirect("/forgot-password");

  const valid = await validateResetToken(slug, token).catch(() => false);
  if (!valid) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-base-200">
        <div className="card bg-base-100 shadow-xl w-full max-w-sm">
          <div className="card-body">
            <div role="alert" className="alert alert-error">
              <span>This reset link is invalid or has expired.</span>
            </div>
            <a href="/forgot-password" className="btn btn-ghost mt-4">
              Request a new link
            </a>
          </div>
        </div>
      </div>
    );
  }

  return <ResetPasswordForm slug={slug} token={token} />;
}
```

**Step 7: Run test to verify it passes**

```bash
npm test -- --reporter=verbose tests/components/ForgotPasswordForm.test.tsx
```

Expected: PASS (2 tests)

**Step 8: Commit**

```bash
cd ..
git add frontend/components/ForgotPasswordForm.tsx frontend/components/ResetPasswordForm.tsx \
  frontend/app/(tenant)/[locale]/forgot-password/ \
  frontend/app/(tenant)/[locale]/reset-password/ \
  frontend/lib/api.ts \
  frontend/tests/components/ForgotPasswordForm.test.tsx
git commit -m "feat: add forgot-password and reset-password pages"
```

---

## Task 8: Backend — User.avatar field + media serving + avatar upload

**Files:**
- Modify: `backend/core/users/models.py`
- Create: `backend/core/users/migrations/000N_add_user_avatar.py` (auto-generated)
- Modify: `backend/core/users/views.py` (add AvatarUploadView)
- Modify: `backend/config/urls.py`
- Modify: `backend/config/settings.py`
- Create: `backend/tests/users/test_avatar_upload.py`

**Step 1: Write the failing test**

Create `backend/tests/users/test_avatar_upload.py`:

```python
"""Tests for avatar upload endpoint."""

import io

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from core.users.models import User


@override_settings(MEDIA_ROOT="/tmp/test_media")
class AvatarUploadTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="alice", email="alice@example.com", password="pass"
        )
        self.client.force_authenticate(user=self.user)

    def _make_image(self, name: str = "photo.jpg") -> io.BytesIO:
        # Minimal valid JPEG header bytes
        content = (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            b"\xff\xd9"
        )
        f = io.BytesIO(content)
        f.name = name
        return f

    def test_upload_jpg_returns_avatar_url(self):
        response = self.client.post(
            "/v1/users/me/avatar/",
            {"avatar": self._make_image()},
            format="multipart",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "avatar_url" in response.data
        assert "/media/avatars/" in response.data["avatar_url"]

    def test_upload_updates_user_avatar_field(self):
        self.client.post(
            "/v1/users/me/avatar/",
            {"avatar": self._make_image()},
            format="multipart",
        )
        self.user.refresh_from_db()
        assert self.user.avatar != ""

    def test_rejects_non_image_file(self):
        f = io.BytesIO(b"not an image")
        f.name = "file.txt"
        response = self.client.post(
            "/v1/users/me/avatar/",
            {"avatar": f},
            format="multipart",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_rejected(self):
        client = APIClient()
        response = client.post(
            "/v1/users/me/avatar/",
            {"avatar": self._make_image()},
            format="multipart",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

**Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/users/test_avatar_upload.py -v
```

Expected: FAIL with 404 (endpoint doesn't exist)

**Step 3: Add avatar field to User model**

Open `backend/core/users/models.py` and add `avatar` field to the `User` model class body:

```python
avatar = models.CharField(max_length=255, blank=True, default="")
```

**Step 4: Generate and apply migration**

```bash
uv run python manage.py makemigrations users --name add_user_avatar
uv run python manage.py migrate_tenants
```

**Step 5: Create AvatarUploadView**

Open `backend/core/users/views.py`. Add these imports at the top:

```python
import os
from pathlib import Path

from django.conf import settings
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
```

Then add the view class:

```python
class AvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
    MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

    def post(self, request: Request) -> Response:
        file = request.FILES.get("avatar")
        if not file:
            return Response({"detail": "No file provided."}, status=400)

        if file.size > self.MAX_SIZE_BYTES:
            return Response({"detail": "File too large. Max 5 MB."}, status=400)

        ext = Path(file.name).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            return Response(
                {"detail": "Only JPEG and PNG files are allowed."}, status=400
            )

        user = request.user
        filename = f"{user.id}{ext}"
        avatar_dir = Path(settings.MEDIA_ROOT) / "avatars"
        avatar_dir.mkdir(parents=True, exist_ok=True)

        with open(avatar_dir / filename, "wb") as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        relative_path = f"avatars/{filename}"
        user.avatar = relative_path
        user.save(update_fields=["avatar"])

        return Response({"avatar_url": f"{settings.MEDIA_URL}{relative_path}"})
```

**Step 6: Add MEDIA settings to settings.py**

Open `backend/config/settings.py` and add:

```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

**Step 7: Register URL and serve media in development**

Open `backend/config/urls.py`. Add the avatar URL and dev media serving:

```python
from django.conf import settings
from django.conf.urls.static import static
from core.users.views import AvatarUploadView

# Add to urlpatterns:
path("v1/users/me/avatar/", AvatarUploadView.as_view(), name="avatar-upload"),

# After urlpatterns definition:
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**Step 8: Run tests to verify they pass**

```bash
uv run pytest tests/users/test_avatar_upload.py -v
```

Expected: PASS (4 tests)

**Step 9: Commit**

```bash
cd ..
git add backend/core/users/models.py backend/core/users/migrations/ \
  backend/core/users/views.py backend/config/urls.py backend/config/settings.py \
  backend/tests/users/test_avatar_upload.py
git commit -m "feat: add User.avatar field, media serving, and avatar upload endpoint"
```

---

## Task 9: Frontend — profile page with avatar upload

**Files:**
- Create: `frontend/components/AvatarUpload.tsx`
- Create: `frontend/app/(tenant)/[locale]/profile/page.tsx`
- Modify: `frontend/lib/api.ts`
- Create: `frontend/tests/components/AvatarUpload.test.tsx`

**Step 1: Add API functions to lib/api.ts**

Append to `frontend/lib/api.ts`:

```typescript
export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  avatar: string;
}

export async function getProfile(token: string): Promise<UserProfile> {
  return request("/v1/users/me/", {
    headers: { Authorization: `Bearer ${token}` },
  }) as Promise<UserProfile>;
}

export async function updateProfile(
  token: string,
  data: { full_name: string }
): Promise<UserProfile> {
  return request("/v1/users/me/", {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  }) as Promise<UserProfile>;
}

export async function uploadAvatar(
  token: string,
  file: File
): Promise<{ avatar_url: string }> {
  const form = new FormData();
  form.append("avatar", file);
  return request("/v1/users/me/avatar/", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  }) as Promise<{ avatar_url: string }>;
}
```

**Note:** The scaffold may not have a `GET /v1/users/me/` endpoint yet. If it doesn't exist, add a minimal `MeView` to `backend/core/users/views.py`:

```python
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user = request.user
        return Response({
            "id": str(user.id),
            "email": user.email,
            "full_name": getattr(user, "full_name", "") or "",
            "avatar": getattr(user, "avatar", "") or "",
        })

    def patch(self, request: Request) -> Response:
        user = request.user
        if "full_name" in request.data:
            user.full_name = request.data["full_name"]
            user.save(update_fields=["full_name"])
        return Response({
            "id": str(user.id),
            "email": user.email,
            "full_name": getattr(user, "full_name", "") or "",
            "avatar": getattr(user, "avatar", "") or "",
        })
```

Register in `backend/config/urls.py`:

```python
path("v1/users/me/", MeView.as_view(), name="me"),
```

Also ensure `User` model has a `full_name` field. Add to `core/users/models.py` if missing:

```python
full_name = models.CharField(max_length=255, blank=True, default="")
```

Then run `makemigrations users --name add_user_full_name` and `migrate_tenants`.

**Step 2: Write the failing test**

Create `frontend/tests/components/AvatarUpload.test.tsx`:

```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import AvatarUpload from "@/components/AvatarUpload";

describe("AvatarUpload", () => {
  it("renders upload button", () => {
    render(<AvatarUpload token="tok" currentAvatar="" onUploaded={vi.fn()} />);
    expect(screen.getByText(/upload photo/i)).toBeTruthy();
  });

  it("rejects files larger than 5MB", async () => {
    const alertMock = vi.spyOn(window, "alert").mockImplementation(() => {});
    render(<AvatarUpload token="tok" currentAvatar="" onUploaded={vi.fn()} />);
    const input = screen.getByLabelText(/upload photo/i) as HTMLInputElement;
    const bigFile = new File(["x".repeat(6 * 1024 * 1024)], "big.jpg", {
      type: "image/jpeg",
    });
    Object.defineProperty(input, "files", { value: [bigFile] });
    fireEvent.change(input);
    expect(alertMock).toHaveBeenCalledWith(
      expect.stringContaining("5 MB")
    );
    alertMock.mockRestore();
  });
});
```

**Step 3: Run test to verify it fails**

```bash
cd frontend && npm test -- --reporter=verbose tests/components/AvatarUpload.test.tsx
```

Expected: FAIL with "Cannot find module"

**Step 4: Create AvatarUpload.tsx**

Create `frontend/components/AvatarUpload.tsx`:

```typescript
"use client";

import { useRef } from "react";
import { uploadAvatar } from "@/lib/api";

interface Props {
  token: string;
  currentAvatar: string;
  onUploaded: (url: string) => void;
}

const MAX_SIZE = 5 * 1024 * 1024;

export default function AvatarUpload({ token, currentAvatar, onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > MAX_SIZE) {
      alert("File is too large. Max 5 MB.");
      return;
    }

    try {
      const { avatar_url } = await uploadAvatar(token, file);
      onUploaded(avatar_url);
    } catch {
      alert("Upload failed. Please try again.");
    }
  }

  const initials = "U";

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="avatar placeholder">
        <div className="bg-neutral text-neutral-content rounded-full w-24">
          {currentAvatar ? (
            <img src={currentAvatar} alt="Profile" className="rounded-full" />
          ) : (
            <span className="text-3xl font-bold">{initials}</span>
          )}
        </div>
      </div>

      <label
        htmlFor="avatar-input"
        className="btn btn-outline btn-sm cursor-pointer"
        aria-label="Upload photo"
      >
        Upload photo
        <input
          id="avatar-input"
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png"
          className="hidden"
          onChange={handleChange}
          aria-label="Upload photo"
        />
      </label>
    </div>
  );
}
```

**Step 5: Create profile page**

Create `frontend/app/(tenant)/[locale]/profile/page.tsx`:

```typescript
"use client";

import { useEffect, useState } from "react";
import AvatarUpload from "@/components/AvatarUpload";
import { getProfile, updateProfile, UserProfile } from "@/lib/api";

function getToken(): string {
  return (
    document.cookie
      .split("; ")
      .find((r) => r.startsWith("access_token="))
      ?.split("=")[1] ?? ""
  );
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [fullName, setFullName] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const token = getToken();
    getProfile(token).then((p) => {
      setProfile(p);
      setFullName(p.full_name);
    });
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    const token = getToken();
    const updated = await updateProfile(token, { full_name: fullName });
    setProfile(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  if (!profile) {
    return (
      <div className="flex justify-center p-8">
        <span className="loading loading-spinner loading-lg" />
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Profile</h1>

      <div className="card bg-base-100 shadow">
        <div className="card-body gap-6">
          <AvatarUpload
            token={getToken()}
            currentAvatar={
              profile.avatar ? `/media/${profile.avatar}` : ""
            }
            onUploaded={(url) =>
              setProfile((p) => (p ? { ...p, avatar: url } : p))
            }
          />

          <form onSubmit={handleSave} className="flex flex-col gap-4">
            <div className="form-control">
              <label className="label" htmlFor="full-name">
                <span className="label-text">Full name</span>
              </label>
              <input
                id="full-name"
                type="text"
                className="input input-bordered"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text">Email</span>
              </label>
              <input
                type="email"
                className="input input-bordered input-disabled"
                value={profile.email}
                readOnly
              />
            </div>

            {saved && (
              <div role="alert" className="alert alert-success text-sm">
                <span>Changes saved.</span>
              </div>
            )}

            <button type="submit" className="btn btn-primary">
              Save changes
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
```

**Step 6: Run test to verify it passes**

```bash
npm test -- --reporter=verbose tests/components/AvatarUpload.test.tsx
```

Expected: PASS (2 tests)

**Step 7: Commit**

```bash
cd ..
git add frontend/components/AvatarUpload.tsx \
  frontend/app/(tenant)/[locale]/profile/ \
  frontend/lib/api.ts \
  frontend/tests/components/AvatarUpload.test.tsx
git commit -m "feat: add profile page with avatar upload"
```

---

## Task 10: Backend — Membership.reports_to field + members API update

**Files:**
- Modify: `backend/core/org/models.py`
- Create: `backend/core/org/migrations/000N_add_membership_reports_to.py` (auto-generated)
- Modify: `backend/core/org/serializers.py`
- Create: `backend/tests/org/test_members_api.py`

**Context:** `reports_to` is a self-referential FK on `Membership`. It allows expressing "within this org, Alice reports to Bob". The members API endpoint will include user name, avatar, and reports_to so the frontend can build the org chart tree client-side.

**Step 1: Write the failing test**

Create `backend/tests/org/test_members_api.py`:

```python
"""Tests for org members endpoint (with reports_to and user info)."""

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from core.org.models import Membership, OrgUnit, Role
from core.users.models import User


class MembersAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = User.objects.create_user(
            username="manager", email="manager@example.com", password="pass",
            full_name="Alice Manager",
        )
        self.report = User.objects.create_user(
            username="report", email="report@example.com", password="pass",
            full_name="Bob Report",
        )
        self.client.force_authenticate(user=self.manager)
        self.unit = OrgUnit.objects.create(name="Acme", slug="acme")
        self.mgr_membership = Membership.objects.create(
            user=self.manager, org_unit=self.unit, role=Role.ADMIN
        )
        self.rpt_membership = Membership.objects.create(
            user=self.report, org_unit=self.unit, role=Role.MEMBER,
            reports_to=self.mgr_membership,
        )

    def test_members_endpoint_includes_user_name(self):
        response = self.client.get(f"/v1/org/units/{self.unit.pk}/members/")
        assert response.status_code == status.HTTP_200_OK
        names = [m["user_name"] for m in response.data]
        assert "Alice Manager" in names

    def test_members_endpoint_includes_reports_to(self):
        response = self.client.get(f"/v1/org/units/{self.unit.pk}/members/")
        bob = next(m for m in response.data if m["user_name"] == "Bob Report")
        assert str(bob["reports_to"]) == str(self.mgr_membership.pk)

    def test_reports_to_null_for_root_member(self):
        response = self.client.get(f"/v1/org/units/{self.unit.pk}/members/")
        alice = next(m for m in response.data if m["user_name"] == "Alice Manager")
        assert alice["reports_to"] is None
```

**Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/org/test_members_api.py -v
```

Expected: FAIL (missing `reports_to` field, missing `user_name` in serializer)

**Step 3: Add reports_to to Membership model**

Open `backend/core/org/models.py`. Add to the `Membership` class:

```python
reports_to = models.ForeignKey(
    "self",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="direct_reports",
)
```

**Step 4: Generate and apply migration**

```bash
uv run python manage.py makemigrations org --name add_membership_reports_to
uv run python manage.py migrate_tenants
```

**Step 5: Update MembershipSerializer**

Open `backend/core/org/serializers.py`. Replace `MembershipSerializer` with:

```python
class MembershipSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = [
            "id", "user", "user_name", "user_avatar",
            "org_unit", "role", "reports_to",
        ]

    def get_user_name(self, obj: Membership) -> str:
        return getattr(obj.user, "full_name", "") or obj.user.email

    def get_user_avatar(self, obj: Membership) -> str:
        avatar = getattr(obj.user, "avatar", "")
        if avatar:
            return f"/media/{avatar}"
        return ""
```

**Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/org/test_members_api.py -v
```

Expected: PASS (3 tests)

**Step 7: Commit**

```bash
cd ..
git add backend/core/org/models.py backend/core/org/migrations/ \
  backend/core/org/serializers.py backend/tests/org/test_members_api.py
git commit -m "feat: add Membership.reports_to and enrich members API with user name and avatar"
```

---

## Task 11: Frontend — org chart page

**Files:**
- Create: `frontend/components/OrgChart.tsx`
- Create: `frontend/app/(tenant)/[locale]/t/[slug]/orgs/[id]/chart/page.tsx`
- Modify: `frontend/types/api.ts`
- Create: `frontend/tests/components/OrgChart.test.tsx`

**Step 1: Install react-organizational-chart**

```bash
cd frontend && npm install react-organizational-chart
```

**Step 2: Add MemberWithUser type to types/api.ts**

Append to `frontend/types/api.ts`:

```typescript
export interface MemberWithUser {
  id: string;
  user: string;
  user_name: string;
  user_avatar: string;
  org_unit: string;
  role: string;
  reports_to: string | null;
}
```

**Step 3: Write the failing test**

Create `frontend/tests/components/OrgChart.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import OrgChart from "@/components/OrgChart";
import type { MemberWithUser } from "@/types/api";

const members: MemberWithUser[] = [
  {
    id: "1",
    user: "u1",
    user_name: "Alice",
    user_avatar: "",
    org_unit: "o1",
    role: "admin",
    reports_to: null,
  },
  {
    id: "2",
    user: "u2",
    user_name: "Bob",
    user_avatar: "",
    org_unit: "o1",
    role: "member",
    reports_to: "1",
  },
];

describe("OrgChart", () => {
  it("renders all member names", () => {
    render(<OrgChart members={members} />);
    expect(screen.getByText("Alice")).toBeTruthy();
    expect(screen.getByText("Bob")).toBeTruthy();
  });

  it("shows empty state when no members", () => {
    render(<OrgChart members={[]} />);
    expect(screen.getByText(/no members/i)).toBeTruthy();
  });
});
```

**Step 4: Run test to verify it fails**

```bash
npm test -- --reporter=verbose tests/components/OrgChart.test.tsx
```

Expected: FAIL with "Cannot find module"

**Step 5: Create OrgChart.tsx**

Create `frontend/components/OrgChart.tsx`:

```typescript
"use client";

import { Tree, TreeNode } from "react-organizational-chart";
import type { MemberWithUser } from "@/types/api";

interface OrgNode {
  member: MemberWithUser;
  children: OrgNode[];
}

function buildTree(members: MemberWithUser[]): OrgNode[] {
  const map = new Map<string, OrgNode>(
    members.map((m) => [m.id, { member: m, children: [] }])
  );
  const roots: OrgNode[] = [];
  for (const node of map.values()) {
    if (!node.member.reports_to || !map.has(node.member.reports_to)) {
      roots.push(node);
    } else {
      map.get(node.member.reports_to)!.children.push(node);
    }
  }
  return roots;
}

function NodeCard({ node }: { node: OrgNode }) {
  const { user_name, user_avatar, role } = node.member;
  const initials = user_name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  const label = (
    <div className="inline-flex flex-col items-center p-3 bg-base-100 border border-base-300 rounded-box shadow-sm min-w-32">
      <div className="avatar placeholder mb-1">
        <div className="bg-neutral text-neutral-content rounded-full w-10">
          {user_avatar ? (
            <img src={user_avatar} alt={user_name} className="rounded-full" />
          ) : (
            <span className="text-sm font-bold">{initials}</span>
          )}
        </div>
      </div>
      <span className="font-semibold text-sm text-center">{user_name}</span>
      <span className="badge badge-ghost badge-sm mt-1">{role}</span>
    </div>
  );

  if (node.children.length === 0) {
    return <TreeNode label={label} />;
  }

  return (
    <TreeNode label={label}>
      {node.children.map((child) => (
        <NodeCard key={child.member.id} node={child} />
      ))}
    </TreeNode>
  );
}

interface Props {
  members: MemberWithUser[];
}

export default function OrgChart({ members }: Props) {
  const roots = buildTree(members);

  if (roots.length === 0) {
    return (
      <p className="text-base-content/60 text-center py-8">
        No members to display.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto py-6">
      <Tree
        label={<div />}
        lineWidth="2px"
        lineColor="currentColor"
        lineBorderRadius="6px"
      >
        {roots.map((root) => (
          <NodeCard key={root.member.id} node={root} />
        ))}
      </Tree>
    </div>
  );
}
```

**Step 6: Create org chart page**

Create `frontend/app/(tenant)/[locale]/t/[slug]/orgs/[id]/chart/page.tsx`:

```typescript
import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import OrgChart from "@/components/OrgChart";
import { request } from "@/lib/api";
import type { MemberWithUser } from "@/types/api";

interface Props {
  params: Promise<{ slug: string; id: string }>;
}

export default async function OrgChartPage({ params }: Props) {
  const { slug, id } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  if (!token) notFound();

  const members = (await request(`/t/${slug}/v1/org/units/${id}/members/`, {
    headers: { Authorization: `Bearer ${token}` },
  })) as MemberWithUser[];

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Org Chart</h1>
        <a href={`/t/${slug}/orgs/${id}`} className="btn btn-ghost btn-sm">
          ← Back to org
        </a>
      </div>
      <OrgChart members={members} />
    </div>
  );
}
```

**Step 7: Run test to verify it passes**

```bash
npm test -- --reporter=verbose tests/components/OrgChart.test.tsx
```

Expected: PASS (2 tests)

**Step 8: Commit**

```bash
cd ..
git add frontend/components/OrgChart.tsx \
  frontend/app/(tenant)/[locale]/t/[slug]/orgs/ \
  frontend/types/api.ts \
  frontend/package.json frontend/package-lock.json \
  frontend/tests/components/OrgChart.test.tsx
git commit -m "feat: add org chart page using react-organizational-chart"
```

---

## Task 12: Backend — InviteToken model + invite endpoints

**Files:**
- Modify: `backend/core/org/models.py`
- Create: `backend/core/org/migrations/000N_add_invite_token.py` (auto-generated)
- Create: `backend/core/org/invite_views.py`
- Modify: `backend/core/org/urls.py`
- Create: `backend/tests/org/test_invites_api.py`

**Step 1: Write the failing tests**

Create `backend/tests/org/test_invites_api.py`:

```python
"""Tests for invite token API endpoints."""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from core.org.models import InviteToken, Membership, OrgUnit, Role
from core.users.models import User


class InviteCreateTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin", email="admin@example.com", password="pass"
        )
        self.client.force_authenticate(user=self.admin)
        self.unit = OrgUnit.objects.create(name="Acme", slug="acme")
        Membership.objects.create(user=self.admin, org_unit=self.unit, role=Role.ADMIN)

    @patch("core.org.invite_views.send_mail")
    def test_create_invite_with_email_sends_mail(self, mock_mail):
        response = self.client.post(
            "/v1/org/invites/",
            {
                "org": str(self.unit.pk),
                "email": "newuser@example.com",
                "role": "member",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert "invite_url" in response.data
        assert mock_mail.called

    @patch("core.org.invite_views.send_mail")
    def test_create_invite_without_email_no_mail(self, mock_mail):
        response = self.client.post(
            "/v1/org/invites/",
            {"org": str(self.unit.pk), "role": "member"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert not mock_mail.called

    def test_list_invites_returns_active_only(self):
        InviteToken.objects.create(
            org=self.unit,
            created_by=self.admin,
            expires_at=timezone.now() + timedelta(days=7),
        )
        InviteToken.objects.create(
            org=self.unit,
            created_by=self.admin,
            expires_at=timezone.now() - timedelta(days=1),  # expired
        )
        response = self.client.get("/v1/org/invites/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1


class InvitePublicTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin2", email="admin2@example.com", password="pass"
        )
        self.unit = OrgUnit.objects.create(name="Beta", slug="beta")

    def _make_invite(self, **kwargs) -> InviteToken:
        return InviteToken.objects.create(
            org=self.unit,
            created_by=self.admin,
            expires_at=timezone.now() + timedelta(days=7),
            **kwargs,
        )

    def test_validate_valid_token(self):
        invite = self._make_invite()
        response = self.client.get(f"/v1/org/invites/{invite.token}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["org_name"] == "Beta"

    def test_validate_expired_token_returns_410(self):
        invite = InviteToken.objects.create(
            org=self.unit,
            created_by=self.admin,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        response = self.client.get(f"/v1/org/invites/{invite.token}/")
        assert response.status_code == status.HTTP_410_GONE

    def test_register_creates_user_and_membership(self):
        invite = self._make_invite(role="member")
        response = self.client.post(
            f"/v1/org/invites/{invite.token}/register/",
            {
                "name": "New User",
                "email": "newuser2@example.com",
                "password": "securepass",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert "access" in response.data
        assert User.objects.filter(email="newuser2@example.com").exists()
        new_user = User.objects.get(email="newuser2@example.com")
        assert Membership.objects.filter(user=new_user, org_unit=self.unit).exists()

    def test_register_marks_token_used(self):
        invite = self._make_invite()
        self.client.post(
            f"/v1/org/invites/{invite.token}/register/",
            {"name": "N", "email": "n@n.com", "password": "securepass"},
        )
        invite.refresh_from_db()
        assert invite.used_at is not None
```

**Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/org/test_invites_api.py -v
```

Expected: FAIL (model and endpoints don't exist)

**Step 3: Add InviteToken to org/models.py**

Open `backend/core/org/models.py` and append:

```python
class InviteToken(models.Model):
    ROLE_CHOICES = [("member", "Member"), ("admin", "Admin")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    org = models.ForeignKey(
        OrgUnit, on_delete=models.CASCADE, related_name="invites"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")
    email = models.EmailField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_invites",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="used_invites",
    )

    class Meta:
        app_label = "org"
        db_table = "invite_tokens"

    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()
```

Make sure `import uuid` and `from django.utils import timezone` are at the top of `org/models.py`, and `from django.conf import settings` is imported.

**Step 4: Generate and apply migration**

```bash
uv run python manage.py makemigrations org --name add_invite_token
uv run python manage.py migrate_tenants
```

**Step 5: Create invite_views.py**

Create `backend/core/org/invite_views.py`:

```python
"""Invite token API endpoints."""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.org.models import InviteToken, Membership, OrgUnit
from core.users.models import User


class InviteListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        now = timezone.now()
        invites = InviteToken.objects.filter(
            used_at__isnull=True,
            expires_at__gt=now,
        ).select_related("org", "created_by")
        data = [
            {
                "id": str(inv.id),
                "token": str(inv.token),
                "org": str(inv.org_id),
                "org_name": inv.org.name,
                "role": inv.role,
                "email": inv.email,
                "expires_at": inv.expires_at.isoformat(),
            }
            for inv in invites
        ]
        return Response(data)

    def post(self, request: Request) -> Response:
        org_id = request.data.get("org")
        role = request.data.get("role", "member")
        email = request.data.get("email") or None

        try:
            org = OrgUnit.objects.get(pk=org_id)
        except OrgUnit.DoesNotExist:
            return Response({"detail": "Org not found."}, status=status.HTTP_404_NOT_FOUND)

        invite = InviteToken.objects.create(
            org=org,
            role=role,
            email=email,
            created_by=request.user,
            expires_at=timezone.now() + timedelta(days=7),
        )
        invite_url = (
            f"{request.scheme}://{request.get_host()}/invite/{invite.token}"
        )

        if email:
            send_mail(
                subject=f"You've been invited to join {org.name}",
                message=(
                    f"You've been invited to join {org.name} as {role}.\n\n"
                    f"Accept the invitation:\n{invite_url}\n\n"
                    "This link expires in 7 days."
                ),
                from_email=None,
                recipient_list=[email],
            )

        return Response(
            {
                "id": str(invite.id),
                "token": str(invite.token),
                "invite_url": invite_url,
            },
            status=status.HTTP_201_CREATED,
        )


class InviteDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, token: uuid.UUID) -> Response:
        try:
            invite = InviteToken.objects.select_related("org").get(token=token)
        except InviteToken.DoesNotExist:
            return Response(
                {"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND
            )
        if not invite.is_valid():
            return Response(
                {"detail": "Invite expired or already used."},
                status=status.HTTP_410_GONE,
            )
        return Response(
            {
                "org_name": invite.org.name,
                "role": invite.role,
                "email": invite.email,
            }
        )

    def delete(self, request: Request, token: uuid.UUID) -> Response:
        InviteToken.objects.filter(token=token).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InviteRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request, token: uuid.UUID) -> Response:
        try:
            invite = InviteToken.objects.select_related("org").get(token=token)
        except InviteToken.DoesNotExist:
            return Response(
                {"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND
            )
        if not invite.is_valid():
            return Response(
                {"detail": "Invite expired or already used."},
                status=status.HTTP_410_GONE,
            )

        name = request.data.get("name", "")
        email = request.data.get("email", "")
        password = request.data.get("password", "")

        if not email or not password:
            return Response(
                {"detail": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(password) < 8:
            return Response(
                {"detail": "Password must be at least 8 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(email=email).exists():
            return Response(
                {"detail": "A user with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create(
            username=email,
            email=email,
            full_name=name,
            password=make_password(password),
        )
        Membership.objects.create(
            user=user,
            org_unit=invite.org,
            role=invite.role,
        )

        invite.used_at = timezone.now()
        invite.used_by = user
        invite.save()

        refresh = RefreshToken.for_user(user)
        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh)},
            status=status.HTTP_201_CREATED,
        )
```

**Step 6: Register invite URL routes**

Open `backend/core/org/urls.py` and add:

```python
from core.org.invite_views import (
    InviteDetailView,
    InviteListCreateView,
    InviteRegisterView,
)

# Add to urlpatterns:
path("invites/", InviteListCreateView.as_view(), name="invite-list"),
path("invites/<uuid:token>/", InviteDetailView.as_view(), name="invite-detail"),
path("invites/<uuid:token>/register/", InviteRegisterView.as_view(), name="invite-register"),
```

**Step 7: Run tests to verify they pass**

```bash
uv run pytest tests/org/test_invites_api.py -v
```

Expected: PASS (7 tests)

**Step 8: Commit**

```bash
cd ..
git add backend/core/org/models.py backend/core/org/migrations/ \
  backend/core/org/invite_views.py backend/core/org/urls.py \
  backend/tests/org/test_invites_api.py
git commit -m "feat: add InviteToken model and invite CRUD/register endpoints"
```

---

## Task 13: Frontend — invite management page

**Files:**
- Create: `frontend/components/InviteModal.tsx`
- Create: `frontend/app/(tenant)/[locale]/t/[slug]/orgs/[id]/invites/page.tsx`
- Modify: `frontend/lib/api.ts`
- Create: `frontend/tests/components/InviteModal.test.tsx`

**Step 1: Add invite API functions to lib/api.ts**

Append to `frontend/lib/api.ts`:

```typescript
export interface Invite {
  id: string;
  token: string;
  org: string;
  org_name: string;
  role: string;
  email: string | null;
  expires_at: string;
  invite_url?: string;
}

export async function listInvites(
  slug: string,
  token: string
): Promise<Invite[]> {
  return request(`/t/${slug}/v1/org/invites/`, {
    headers: { Authorization: `Bearer ${token}` },
  }) as Promise<Invite[]>;
}

export async function createInvite(
  slug: string,
  token: string,
  data: { org: string; role: string; email?: string }
): Promise<Invite> {
  return request(`/t/${slug}/v1/org/invites/`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  }) as Promise<Invite>;
}

export async function revokeInvite(
  slug: string,
  token: string,
  inviteToken: string
): Promise<void> {
  await request(`/t/${slug}/v1/org/invites/${inviteToken}/`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}
```

**Step 2: Write the failing test**

Create `frontend/tests/components/InviteModal.test.tsx`:

```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import InviteModal from "@/components/InviteModal";

describe("InviteModal", () => {
  it("renders the create invite button", () => {
    render(
      <InviteModal
        slug="acme"
        orgId="org-1"
        token="access-tok"
        onCreated={vi.fn()}
      />
    );
    expect(screen.getByText(/create invitation/i)).toBeTruthy();
  });

  it("shows email and role fields when modal is open", () => {
    render(
      <InviteModal
        slug="acme"
        orgId="org-1"
        token="access-tok"
        onCreated={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText(/create invitation/i));
    expect(screen.getByLabelText(/email/i)).toBeTruthy();
    expect(screen.getByLabelText(/role/i)).toBeTruthy();
  });
});
```

**Step 3: Run test to verify it fails**

```bash
cd frontend && npm test -- --reporter=verbose tests/components/InviteModal.test.tsx
```

Expected: FAIL with "Cannot find module"

**Step 4: Create InviteModal.tsx**

Create `frontend/components/InviteModal.tsx`:

```typescript
"use client";

import { useState } from "react";
import { createInvite, Invite } from "@/lib/api";

interface Props {
  slug: string;
  orgId: string;
  token: string;
  onCreated: (invite: Invite) => void;
}

export default function InviteModal({ slug, orgId, token, onCreated }: Props) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Invite | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const invite = await createInvite(slug, token, {
        org: orgId,
        role,
        ...(email ? { email } : {}),
      });
      setResult(invite);
      onCreated(invite);
    } finally {
      setLoading(false);
    }
  }

  function copyLink() {
    if (result?.invite_url) {
      navigator.clipboard.writeText(result.invite_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  function close() {
    setOpen(false);
    setEmail("");
    setRole("member");
    setResult(null);
    setCopied(false);
  }

  return (
    <>
      <button className="btn btn-primary btn-sm" onClick={() => setOpen(true)}>
        Create invitation
      </button>

      {open && (
        <div className="modal modal-open">
          <div className="modal-box">
            <h3 className="font-bold text-lg mb-4">Create Invitation</h3>

            {result ? (
              <div className="flex flex-col gap-3">
                <p className="text-sm text-base-content/70">
                  Invitation created. Share this link:
                </p>
                <div className="join w-full">
                  <input
                    className="input input-bordered join-item flex-1 text-sm"
                    value={result.invite_url ?? ""}
                    readOnly
                  />
                  <button
                    className="btn join-item"
                    onClick={copyLink}
                  >
                    {copied ? "Copied!" : "Copy link"}
                  </button>
                </div>
                <button className="btn btn-ghost btn-sm mt-2" onClick={close}>
                  Close
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="flex flex-col gap-3">
                <div className="form-control">
                  <label className="label" htmlFor="invite-email">
                    <span className="label-text">Email (optional)</span>
                  </label>
                  <input
                    id="invite-email"
                    type="email"
                    className="input input-bordered"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Leave blank for link-only"
                    aria-label="Email"
                  />
                </div>

                <div className="form-control">
                  <label className="label" htmlFor="invite-role">
                    <span className="label-text">Role</span>
                  </label>
                  <select
                    id="invite-role"
                    className="select select-bordered"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    aria-label="Role"
                  >
                    <option value="member">Member</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>

                <div className="modal-action">
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={close}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={loading}
                  >
                    {loading && (
                      <span className="loading loading-spinner loading-sm" />
                    )}
                    Send invitation
                  </button>
                </div>
              </form>
            )}
          </div>
          <div className="modal-backdrop" onClick={close} />
        </div>
      )}
    </>
  );
}
```

**Step 5: Create invite management page**

Create `frontend/app/(tenant)/[locale]/t/[slug]/orgs/[id]/invites/page.tsx`:

```typescript
"use client";

import { useEffect, useState } from "react";
import InviteModal from "@/components/InviteModal";
import { listInvites, revokeInvite, Invite } from "@/lib/api";

interface Props {
  params: { slug: string; id: string };
}

function getToken(): string {
  return (
    document.cookie
      .split("; ")
      .find((r) => r.startsWith("access_token="))
      ?.split("=")[1] ?? ""
  );
}

export default function InvitesPage({ params }: Props) {
  const { slug, id: orgId } = params;
  const [invites, setInvites] = useState<Invite[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    listInvites(slug, token)
      .then(setInvites)
      .finally(() => setLoading(false));
  }, [slug]);

  async function handleRevoke(inviteToken: string) {
    const token = getToken();
    await revokeInvite(slug, token, inviteToken);
    setInvites((prev) => prev.filter((i) => i.token !== inviteToken));
  }

  function handleCreated(invite: Invite) {
    setInvites((prev) => [...prev, invite]);
  }

  function copyLink(url: string) {
    navigator.clipboard.writeText(url);
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Invitations</h1>
        <InviteModal
          slug={slug}
          orgId={orgId}
          token={getToken()}
          onCreated={handleCreated}
        />
      </div>

      {loading ? (
        <div className="flex justify-center py-8">
          <span className="loading loading-spinner loading-lg" />
        </div>
      ) : invites.length === 0 ? (
        <p className="text-base-content/60 text-center py-8">
          No active invitations.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Role</th>
                <th>Expires</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {invites.map((invite) => (
                <tr key={invite.id}>
                  <td>{invite.email ?? <em className="text-base-content/50">Link only</em>}</td>
                  <td>
                    <span className="badge badge-ghost">{invite.role}</span>
                  </td>
                  <td className="text-sm text-base-content/70">
                    {new Date(invite.expires_at).toLocaleDateString()}
                  </td>
                  <td className="flex gap-2">
                    <button
                      className="btn btn-xs btn-ghost"
                      onClick={() =>
                        copyLink(
                          `${window.location.origin}/invite/${invite.token}`
                        )
                      }
                    >
                      Copy link
                    </button>
                    <button
                      className="btn btn-xs btn-error btn-outline"
                      onClick={() => handleRevoke(invite.token)}
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

**Step 6: Run test to verify it passes**

```bash
npm test -- --reporter=verbose tests/components/InviteModal.test.tsx
```

Expected: PASS (2 tests)

**Step 7: Commit**

```bash
cd ..
git add frontend/components/InviteModal.tsx \
  frontend/app/(tenant)/[locale]/t/[slug]/orgs/[id]/invites/ \
  frontend/lib/api.ts \
  frontend/tests/components/InviteModal.test.tsx
git commit -m "feat: add invite management page with create, copy-link, and revoke"
```

---

## Task 14: Frontend — invite registration page

**Files:**
- Create: `frontend/components/InviteRegisterForm.tsx`
- Create: `frontend/app/(tenant)/[locale]/invite/[token]/page.tsx`
- Modify: `frontend/lib/api.ts`
- Create: `frontend/tests/components/InviteRegisterForm.test.tsx`

**Step 1: Add invite public API functions to lib/api.ts**

Append to `frontend/lib/api.ts`:

```typescript
export interface InviteInfo {
  org_name: string;
  role: string;
  email: string | null;
}

export async function getInviteInfo(
  slug: string,
  inviteToken: string
): Promise<InviteInfo> {
  return request(`/t/${slug}/v1/org/invites/${inviteToken}/`) as Promise<InviteInfo>;
}

export async function registerViaInvite(
  slug: string,
  inviteToken: string,
  data: { name: string; email: string; password: string }
): Promise<{ access: string; refresh: string }> {
  return request(`/t/${slug}/v1/org/invites/${inviteToken}/register/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  }) as Promise<{ access: string; refresh: string }>;
}
```

**Step 2: Write the failing test**

Create `frontend/tests/components/InviteRegisterForm.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import InviteRegisterForm from "@/components/InviteRegisterForm";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  registerViaInvite: vi
    .fn()
    .mockResolvedValue({ access: "tok", refresh: "ref" }),
}));

describe("InviteRegisterForm", () => {
  const props = {
    slug: "acme",
    inviteToken: "some-token",
    orgName: "Acme Corp",
    role: "member",
    prefillEmail: "",
  };

  it("renders org name and role", () => {
    render(<InviteRegisterForm {...props} />);
    expect(screen.getByText(/Acme Corp/)).toBeTruthy();
    expect(screen.getByText(/member/i)).toBeTruthy();
  });

  it("renders name, email and password fields", () => {
    render(<InviteRegisterForm {...props} />);
    expect(screen.getByLabelText(/full name/i)).toBeTruthy();
    expect(screen.getByLabelText(/email/i)).toBeTruthy();
    expect(screen.getByLabelText(/password/i)).toBeTruthy();
  });

  it("shows error when passwords don't match", async () => {
    render(<InviteRegisterForm {...props} />);
    fireEvent.change(screen.getByLabelText(/full name/i), {
      target: { value: "Test" },
    });
    fireEvent.change(screen.getByLabelText(/^email/i), {
      target: { value: "t@t.com" },
    });
    fireEvent.change(screen.getByLabelText(/^password/i), {
      target: { value: "pass1234" },
    });
    fireEvent.change(screen.getByLabelText(/confirm/i), {
      target: { value: "different" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeTruthy();
    });
  });
});
```

**Step 3: Run test to verify it fails**

```bash
cd frontend && npm test -- --reporter=verbose tests/components/InviteRegisterForm.test.tsx
```

Expected: FAIL with "Cannot find module"

**Step 4: Create InviteRegisterForm.tsx**

Create `frontend/components/InviteRegisterForm.tsx`:

```typescript
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { registerViaInvite } from "@/lib/api";

interface Props {
  slug: string;
  inviteToken: string;
  orgName: string;
  role: string;
  prefillEmail: string;
}

export default function InviteRegisterForm({
  slug,
  inviteToken,
  orgName,
  role,
  prefillEmail,
}: Props) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState(prefillEmail);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const { access } = await registerViaInvite(slug, inviteToken, {
        name,
        email,
        password,
      });
      document.cookie = `access_token=${access}; path=/; SameSite=Lax`;
      router.push(`/t/${slug}/dashboard`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-base-200">
      <div className="card bg-base-100 shadow-xl w-full max-w-sm">
        <div className="card-body">
          <div className="mb-4">
            <h1 className="card-title text-2xl">You&apos;ve been invited</h1>
            <p className="text-sm text-base-content/70 mt-1">
              Join <strong>{orgName}</strong> as{" "}
              <span className="badge badge-ghost badge-sm">{role}</span>
            </p>
          </div>

          {error && (
            <div role="alert" className="alert alert-error text-sm">
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <div className="form-control">
              <label className="label" htmlFor="name">
                <span className="label-text">Full name</span>
              </label>
              <input
                id="name"
                type="text"
                className="input input-bordered"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                autoComplete="name"
                aria-label="Full name"
              />
            </div>

            <div className="form-control">
              <label className="label" htmlFor="email">
                <span className="label-text">Email</span>
              </label>
              <input
                id="email"
                type="email"
                className="input input-bordered"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                aria-label="Email"
              />
            </div>

            <div className="form-control">
              <label className="label" htmlFor="password">
                <span className="label-text">Password</span>
              </label>
              <input
                id="password"
                type="password"
                className="input input-bordered"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
                aria-label="Password"
              />
            </div>

            <div className="form-control">
              <label className="label" htmlFor="confirm">
                <span className="label-text">Confirm password</span>
              </label>
              <input
                id="confirm"
                type="password"
                className="input input-bordered"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                autoComplete="new-password"
                aria-label="Confirm password"
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary mt-2"
              disabled={loading}
            >
              {loading && (
                <span className="loading loading-spinner loading-sm" />
              )}
              Create account
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
```

**Step 5: Create invite registration page**

Create `frontend/app/(tenant)/[locale]/invite/[token]/page.tsx`:

```typescript
import { headers } from "next/headers";
import { notFound } from "next/navigation";
import InviteRegisterForm from "@/components/InviteRegisterForm";
import { getInviteInfo } from "@/lib/api";
import { getTenantSlugFromHostname } from "@/lib/tenant";

interface Props {
  params: Promise<{ token: string }>;
}

export default async function InviteRegisterPage({ params }: Props) {
  const { token } = await params;
  const host = (await headers()).get("host") ?? "";
  const slug = getTenantSlugFromHostname(host) ?? "demo";
  if (!slug) notFound();

  let info;
  try {
    info = await getInviteInfo(slug, token);
  } catch {
    return (
      <div className="min-h-screen flex items-center justify-center bg-base-200">
        <div className="card bg-base-100 shadow-xl w-full max-w-sm">
          <div className="card-body">
            <div role="alert" className="alert alert-error">
              <span>This invitation link is invalid or has expired.</span>
            </div>
            <a href="/login" className="btn btn-ghost mt-4">
              Go to sign in
            </a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <InviteRegisterForm
      slug={slug}
      inviteToken={token}
      orgName={info.org_name}
      role={info.role}
      prefillEmail={info.email ?? ""}
    />
  );
}
```

**Step 6: Run test to verify it passes**

```bash
npm test -- --reporter=verbose tests/components/InviteRegisterForm.test.tsx
```

Expected: PASS (3 tests)

**Step 7: Commit**

```bash
cd ..
git add frontend/components/InviteRegisterForm.tsx \
  frontend/app/(tenant)/[locale]/invite/ \
  frontend/lib/api.ts \
  frontend/tests/components/InviteRegisterForm.test.tsx
git commit -m "feat: add invite registration page"
```

---

## Task 15: Full test suite pass

**Step 1: Run all backend tests**

```bash
cd backend && uv run pytest --tb=short -q
```

Expected: all PASSED.

**Step 2: Run backend linter**

```bash
uv run ruff check . && uv run ruff format --check .
```

Fix any issues:

```bash
uv run ruff check --fix . && uv run ruff format .
```

**Step 3: Run all frontend tests**

```bash
cd ../frontend && npm test
```

Expected: all PASSED.

**Step 4: Run TypeScript type check**

```bash
npx tsc --noEmit
```

Fix any type errors before continuing.

**Step 5: Smoke test — start dev server and verify pages load**

```bash
npm run dev
```

Manually verify these routes load without console errors:
- `http://localhost:3000/login`
- `http://localhost:3000/forgot-password`
- `http://localhost:3000/profile`

**Step 6: Commit any remaining fixes**

```bash
cd ..
git add -u && git commit -m "fix: linting, type errors, and test failures from full suite pass"
```

(Skip this commit if there are no changes.)

---

## Summary

After completing all tasks, the following features are live:

| Feature | Backend | Frontend |
|---|---|---|
| Tailwind CSS + DaisyUI | — | ✓ |
| `localePrefix: "never"` | — | ✓ |
| ThemeProvider + dark mode | — | ✓ |
| Polished login (DaisyUI) | — | ✓ |
| Password reset via email | `PasswordResetToken` + 3 endpoints | ✓ |
| User profile + avatar upload | `User.avatar` + `MeView` + `AvatarUploadView` | ✓ |
| Org chart | `Membership.reports_to` + enriched members API | ✓ |
| Invite system | `InviteToken` + 5 endpoints | ✓ |
