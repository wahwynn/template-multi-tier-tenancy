"""Management command: seed_tenant.

Usage:
    uv run manage.py seed_tenant <slug>

Seeds a tenant schema with sample data for demo or development use.
Idempotent: safe to run multiple times.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from app.org.models import Membership, OrgUnit, Role

User = get_user_model()


class Command(BaseCommand):
    help = "Seed a tenant schema with sample demo data."

    def add_arguments(self, parser) -> None:
        parser.add_argument("slug", type=str)

    def handle(self, *args, **options) -> None:
        slug: str = options["slug"]
        tenant = next((t for t in settings.TENANTS if t["slug"] == slug), None)
        if tenant is None:
            raise CommandError(f"Tenant '{slug}' not found in TENANTS config.")

        # Root org unit
        corp, _ = OrgUnit.objects.get_or_create(
            slug=f"{slug}-corp",
            defaults={"name": f"{slug.title()} Corp", "node_type": "org"},
        )

        # Demo departments
        for dept_slug, dept_name in [("engineering", "Engineering"), ("sales", "Sales")]:
            OrgUnit.objects.get_or_create(
                slug=dept_slug,
                parent=corp,
                defaults={"name": dept_name, "node_type": "department"},
            )

        # Admin user
        email = f"admin@{slug}.local"
        user, created = User.objects.get_or_create(
            username=email,
            defaults={"email": email, "is_staff": True},
        )
        if created:
            user.set_password("demo-password-change-me")
            user.save()

        Membership.objects.get_or_create(
            user=user, org_unit=corp, defaults={"role": Role.OWNER}
        )

        if options["verbosity"] > 0:
            self.stdout.write(self.style.SUCCESS(f"Seeded tenant '{slug}'."))
