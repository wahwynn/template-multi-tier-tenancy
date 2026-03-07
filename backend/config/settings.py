"""Django settings for multi-tenant scaffold."""

from __future__ import annotations

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Security ---
SECRET_KEY: str = os.environ.get("JWT_SECRET", "dev-secret-key-change-in-production")
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
import dj_database_url  # noqa: E402

DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL", "postgres://app:app@localhost:5432/app")
    )
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
