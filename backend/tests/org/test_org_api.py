"""Tests for OrgUnit API endpoints."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from app.org.models import Membership, OrgUnit, Role

User = get_user_model()

TENANTS_CONFIG = [{"slug": "acme", "schema": "acme", "domains": []}]


@override_settings(TENANTS=TENANTS_CONFIG)
class TestOrgUnitAPI(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="alice", password="pass", email="alice@example.com")
        self.corp = OrgUnit.objects.create(name="Acme Corp", slug="acme-corp", node_type="org")
        Membership.objects.create(user=self.user, org_unit=self.corp, role=Role.ADMIN)
        self.client.force_authenticate(user=self.user)

    def test_list_org_units_returns_accessible_units(self):
        response = self.client.get("/t/acme/v1/org/units/")
        assert response.status_code == 200
        slugs = [u["slug"] for u in response.data["results"]]
        assert "acme-corp" in slugs

    def test_create_org_unit(self):
        response = self.client.post(
            "/t/acme/v1/org/units/",
            {
                "name": "Engineering",
                "slug": "engineering",
                "node_type": "department",
                "parent": str(self.corp.pk),
                "isolation_policy": "open",
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["slug"] == "engineering"

    def test_get_org_unit_detail(self):
        response = self.client.get(f"/t/acme/v1/org/units/{self.corp.pk}/")
        assert response.status_code == 200
        assert response.data["name"] == "Acme Corp"

    def test_get_ancestors(self):
        dept = OrgUnit.objects.create(name="Dept", slug="dept", parent=self.corp)
        response = self.client.get(f"/t/acme/v1/org/units/{dept.pk}/ancestors/")
        assert response.status_code == 200
        assert any(u["slug"] == "acme-corp" for u in response.data)

    def test_get_descendants(self):
        OrgUnit.objects.create(name="Dept", slug="dept", parent=self.corp)
        response = self.client.get(f"/t/acme/v1/org/units/{self.corp.pk}/descendants/")
        assert response.status_code == 200
        assert any(u["slug"] == "dept" for u in response.data)

    def test_unauthenticated_request_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/t/acme/v1/org/units/")
        assert response.status_code == 401

    def test_list_members(self):
        response = self.client.get(f"/t/acme/v1/org/units/{self.corp.pk}/members/")
        assert response.status_code == 200

    def test_add_member(self):
        new_user = User.objects.create_user(username="bob", password="pass")
        response = self.client.post(
            f"/t/acme/v1/org/units/{self.corp.pk}/members/",
            {"user": new_user.pk, "org_unit": str(self.corp.pk), "role": "member"},
            format="json",
        )
        assert response.status_code == 201
