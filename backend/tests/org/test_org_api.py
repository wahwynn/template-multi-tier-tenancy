"""Tests for OrgUnit API endpoints."""

from unittest.mock import MagicMock, patch

from core.org.models import Membership, OrgUnit, Role
from core.users.models import User
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

TENANTS_CONFIG = [
    {"slug": "test", "schema": "public", "domains": ["testserver"], "demo": False},
]


class OrgUnitAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="alice", email="alice@example.com", password="pass")
        self.client.force_authenticate(user=self.user)
        self.unit = OrgUnit.objects.create(name="Acme Corp", slug="acme", node_type="org")
        Membership.objects.create(user=self.user, org_unit=self.unit, role=Role.OWNER)

    def _get(self, url):
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        with override_settings(TENANTS=TENANTS_CONFIG), patch("core.tenants.middleware.connection", mock_conn):
            return self.client.get(url)

    def _post(self, url, data):
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        with override_settings(TENANTS=TENANTS_CONFIG), patch("core.tenants.middleware.connection", mock_conn):
            return self.client.post(url, data)

    def test_list_org_units(self):
        response = self._get("/v1/org/units/")
        assert response.status_code == status.HTTP_200_OK

    def test_create_org_unit(self):
        response = self._post(
            "/v1/org/units/",
            {"name": "Engineering", "slug": "eng", "node_type": "department", "parent": str(self.unit.pk)},
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_get_org_unit_detail(self):
        response = self._get(f"/v1/org/units/{self.unit.pk}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Acme Corp"

    def test_unauthenticated_request_rejected(self):
        client = APIClient()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        with override_settings(TENANTS=TENANTS_CONFIG), patch("core.tenants.middleware.connection", mock_conn):
            response = client.get("/v1/org/units/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
