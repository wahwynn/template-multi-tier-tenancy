"""Management command: migrate_shared."""

from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Run Django migrations for shared apps into the 'shared' schema."

    def handle(self, *args: object, **options: object) -> None:
        self.stdout.write("Ensuring 'shared' schema exists...")
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS shared")

        self.stdout.write("Migrating shared schema...")
        original_options = connection.settings_dict.get("OPTIONS", {}).copy()
        try:
            connection.settings_dict.setdefault("OPTIONS", {})
            connection.settings_dict["OPTIONS"]["options"] = "-c search_path=shared,public"
            connection.close()
            call_command("migrate", verbosity=options["verbosity"])
            self.stdout.write(self.style.SUCCESS("  'shared' OK"))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"  'shared' FAILED: {exc}"))
            raise
        finally:
            connection.settings_dict["OPTIONS"] = original_options
            connection.close()
