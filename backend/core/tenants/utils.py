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
