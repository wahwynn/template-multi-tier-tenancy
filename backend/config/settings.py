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
    "django.contrib.sessions",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "app.tenants",
    "app.org",
]

# SessionMiddleware and AuthenticationMiddleware intentionally omitted.
# This is a stateless JWT/API-key API — no server-side sessions or CSRF.
# CorsMiddleware must be before CommonMiddleware (and any middleware that
# generates responses, e.g. TenantMiddleware) so preflight OPTIONS requests
# are handled before the tenant resolution logic runs.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "app.tenants.middleware.TenantMiddleware",
    "django.middleware.common.CommonMiddleware",
]

# --- CORS ---
# In development allow the local Next.js dev server.
# In production set CORS_ALLOWED_ORIGINS (or CORS_ALLOWED_ORIGIN_REGEXES)
# to the actual frontend domain(s).
_cors_origins_env = os.environ.get("CORS_ALLOWED_ORIGINS", "")
CORS_ALLOWED_ORIGINS: list[str] = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
if not CORS_ALLOWED_ORIGINS:
    # Fall back to permissive mode only when DEBUG is on
    CORS_ALLOW_ALL_ORIGINS: bool = DEBUG

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database ---
DATABASES = {"default": dj_database_url.parse(os.environ.get("DATABASE_URL", "postgres://app:app@localhost:5432/app"))}

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
AUTHENTICATION_BACKENDS = ["app.org.authentication.EmailAuthBackend"]

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

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(seconds=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRY", "3600"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(seconds=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRY", "86400"))),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en-us"
USE_TZ = True
