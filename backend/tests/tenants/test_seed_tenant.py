"""Tests for seed_tenant management command."""

from unittest.mock import MagicMock, patch

from django.test import override_settings

TENANTS_CONFIG = [{"slug": "demo", "schema": "demo", "domains": []}]


@override_settings(TENANTS=TENANTS_CONFIG)
@patch("core.tenants.management.commands.seed_tenant.Membership")
@patch("core.tenants.management.commands.seed_tenant.User")
@patch("core.tenants.management.commands.seed_tenant.OrgUnit")
@patch("core.tenants.management.commands.seed_tenant.connection")
def test_seed_tenant_sets_search_path_with_shared(mock_connection, mock_org_unit, mock_user, mock_membership):
    mock_cursor = MagicMock()
    mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_org_unit.objects.get_or_create.return_value = (MagicMock(), True)
    mock_user.objects.get_or_create.return_value = (MagicMock(), False)
    mock_membership.objects.get_or_create.return_value = (MagicMock(), True)

    from core.tenants.management.commands.seed_tenant import Command
    cmd = Command()
    cmd.handle(slug="demo", verbosity=0)

    sql = mock_cursor.execute.call_args[0][0]
    assert "shared" in sql
    assert "demo" in sql
