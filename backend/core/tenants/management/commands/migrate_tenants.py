"""Management command: migrate_tenants."""

from __future__ import annotations

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

from core.tenants.utils import safe_schema


class Command(BaseCommand):
    help = "Run Django migrations across all (or one) tenant schemas."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--schema",
            type=str,
            default=None,
            help="Limit to a single schema. Defaults to all tenants.",
        )

    def handle(self, *args: object, **options: object) -> None:
        target_schema: str | None = options.get("schema")

        tenants = settings.TENANTS
        if target_schema:
            tenants = [t for t in tenants if t["schema"] == target_schema]

        for tenant in tenants:
            schema = safe_schema(tenant["schema"])
            self.stdout.write(f"Migrating schema '{schema}'...")
            original_options = connection.settings_dict.get("OPTIONS", {}).copy()
            try:
                connection.settings_dict.setdefault("OPTIONS", {})
                connection.settings_dict["OPTIONS"]["options"] = f"-c search_path={schema},shared,public"
                connection.close()
                call_command("migrate", verbosity=options["verbosity"])
                self.stdout.write(self.style.SUCCESS(f"  '{schema}' OK"))
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"  '{schema}' FAILED: {exc}"))
                raise
            finally:
                connection.settings_dict["OPTIONS"] = original_options
                connection.close()
