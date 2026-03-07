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

    def handle(self, *args, **options) -> None:
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
                connection.settings_dict["OPTIONS"]["options"] = f"-c search_path={schema},public"
                connection.close()  # force reconnect with new options
                call_command("migrate", verbosity=options["verbosity"])
                self.stdout.write(self.style.SUCCESS(f"  '{schema}' OK"))
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"  '{schema}' FAILED: {exc}"))
                raise
            finally:
                connection.settings_dict["OPTIONS"] = original_options
                connection.close()  # reset to default options
