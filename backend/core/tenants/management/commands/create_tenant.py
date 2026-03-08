"""Management command: create_tenant."""

from __future__ import annotations

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from core.tenants.utils import safe_schema


class Command(BaseCommand):
    help = "Create a PostgreSQL schema for a tenant and run migrations."

    def add_arguments(self, parser) -> None:
        parser.add_argument("slug", type=str, help="Tenant slug (must exist in TENANTS config)")

    def handle(self, *args: object, **options: object) -> None:
        slug: str = options["slug"]
        tenant = next((t for t in settings.TENANTS if t["slug"] == slug), None)
        if tenant is None:
            raise CommandError(f"Tenant '{slug}' not found in TENANTS config.")

        schema = safe_schema(tenant["schema"])
        self.stdout.write(f"Creating schema '{schema}'...")
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

        self.stdout.write(f"Running migrations for schema '{schema}'...")
        call_command("migrate_tenants", "--schema", schema, verbosity=options["verbosity"])
        self.stdout.write(self.style.SUCCESS(f"Tenant '{slug}' ready."))
