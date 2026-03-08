"""Tests for tenant management commands."""

from unittest.mock import MagicMock, patch

import pytest
from django.core.management.base import CommandError
from django.test import override_settings

from core.tenants.management.commands.create_tenant import Command as CreateTenantCommand
from core.tenants.management.commands.migrate_shared import Command as MigrateSharedCommand
from core.tenants.management.commands.migrate_tenants import Command as MigrateTenantsCommand

TENANTS_CONFIG = [
    {"slug": "acme", "schema": "acme", "domains": ["acme.localhost"]},
    {"slug": "demo", "schema": "demo", "domains": []},
]


@patch("core.tenants.management.commands.migrate_shared.call_command")
@patch("core.tenants.management.commands.migrate_shared.connection")
def test_migrate_shared_creates_schema_and_runs_migrate(mock_connection, mock_call_command):
    mock_cursor = MagicMock()
    mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_connection.settings_dict = {"OPTIONS": {}}

    cmd = MigrateSharedCommand()
    cmd.handle(verbosity=1)

    mock_cursor.execute.assert_called_once_with("CREATE SCHEMA IF NOT EXISTS shared")
    mock_call_command.assert_called_once_with("migrate", verbosity=1)


@override_settings(TENANTS=TENANTS_CONFIG)
@patch("core.tenants.management.commands.create_tenant.call_command")
@patch("core.tenants.management.commands.create_tenant.connection")
def test_create_tenant_creates_schema_and_runs_migrations(mock_connection, mock_call_command):
    mock_cursor = MagicMock()
    mock_connection.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_connection.cursor.return_value.__exit__ = MagicMock(return_value=False)

    cmd = CreateTenantCommand()
    cmd.handle(slug="acme", verbosity=1)

    mock_cursor.execute.assert_called_once_with("CREATE SCHEMA IF NOT EXISTS acme")
    mock_call_command.assert_called_once_with("migrate_tenants", "--schema", "acme", verbosity=1)


@override_settings(TENANTS=TENANTS_CONFIG)
def test_create_tenant_raises_error_for_unknown_slug():
    cmd = CreateTenantCommand()
    with pytest.raises(CommandError):
        cmd.handle(slug="unknown", verbosity=1)


@override_settings(TENANTS=TENANTS_CONFIG)
@patch("core.tenants.management.commands.migrate_tenants.call_command")
@patch("core.tenants.management.commands.migrate_tenants.connection")
def test_migrate_tenants_runs_migrate_for_all_tenants(mock_connection, mock_call_command):
    mock_connection.settings_dict = {"OPTIONS": {}}

    cmd = MigrateTenantsCommand()
    cmd.handle(schema=None, verbosity=1)

    assert mock_call_command.call_count == 2
