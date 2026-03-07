"""Tests for seed_tenant management command."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from app.tenants.management.commands.seed_tenant import Command
from app.org.models import OrgUnit

User = get_user_model()

TENANTS_CONFIG = [{"slug": "demo", "schema": "demo", "domains": [], "demo": True}]


@override_settings(TENANTS=TENANTS_CONFIG)
class TestSeedTenant(TestCase):
    def test_seed_creates_root_org_unit(self):
        cmd = Command()
        cmd.handle(slug="demo", verbosity=0)
        assert OrgUnit.objects.filter(slug="demo-corp").exists()

    def test_seed_creates_admin_user(self):
        cmd = Command()
        cmd.handle(slug="demo", verbosity=0)
        assert User.objects.filter(username="admin@demo.local").exists()

    def test_seed_is_idempotent(self):
        cmd = Command()
        cmd.handle(slug="demo", verbosity=0)
        cmd.handle(slug="demo", verbosity=0)
        assert OrgUnit.objects.filter(slug="demo-corp").count() == 1
