"""Org hierarchy models."""

from __future__ import annotations

import uuid
from typing import ClassVar

from django.conf import settings
from django.db import models


class IsolationPolicy(models.TextChoices):
    OPEN = "open", "Open"
    ISOLATED = "isolated", "Isolated"
    INHERIT_ONLY = "inherit_only", "Inherit Only"
    VISIBLE_ONLY = "visible_only", "Visible Only"


class Role(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    MEMBER = "member", "Member"
    VIEWER = "viewer", "Viewer"


class OrgUnit(models.Model):
    """A node in the organisational hierarchy."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    node_type = models.CharField(max_length=100, default="org")
    isolation_policy = models.CharField(
        max_length=20,
        choices=IsolationPolicy.choices,
        default=IsolationPolicy.OPEN,
    )

    class Meta:
        app_label = "org"
        db_table = "org_units"

    def __str__(self) -> str:
        return self.name

    def get_ancestors(self) -> list[OrgUnit]:
        """Return list of ancestors from immediate parent to root (nearest first).

        Uses a recursive CTE to avoid N+1 queries.
        """
        if self.parent_id is None:
            return []

        from django.db import connection

        pk_val = self.pk.hex if connection.vendor == "sqlite" else str(self.pk)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH RECURSIVE ancestors AS (
                    SELECT id, parent_id, 1 AS depth
                    FROM org_units
                    WHERE id = (SELECT parent_id FROM org_units WHERE id = %s)
                    UNION ALL
                    SELECT o.id, o.parent_id, a.depth + 1
                    FROM org_units o
                    INNER JOIN ancestors a ON o.id = a.parent_id
                )
                SELECT id FROM ancestors ORDER BY depth ASC
                """,
                [pk_val],
            )
            raw_ids = [row[0] for row in cursor.fetchall()]

        if not raw_ids:
            return []

        # Normalise IDs (SQLite returns hex without dashes, Postgres returns UUID strings)
        import uuid as uuid_module

        def normalise(raw: str) -> str:
            s = str(raw)
            if "-" not in s:
                return str(uuid_module.UUID(s))
            return s

        normalised_ids = [normalise(i) for i in raw_ids]
        units_by_pk = {str(u.pk): u for u in OrgUnit.objects.filter(pk__in=normalised_ids)}
        return [units_by_pk[nid] for nid in normalised_ids if nid in units_by_pk]

    def get_descendants(self) -> list[OrgUnit]:
        """Return all descendant nodes via recursive CTE."""
        from django.db import connection

        # Format the UUID to match how the backend stores it.
        # PostgreSQL stores UUIDs with dashes; SQLite stores them without.
        vendor = connection.vendor
        pk_str = self.pk.hex if vendor == "sqlite" else str(self.pk)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH RECURSIVE descendants AS (
                    SELECT id FROM org_units WHERE parent_id = %s
                    UNION ALL
                    SELECT o.id FROM org_units o
                    INNER JOIN descendants d ON o.parent_id = d.id
                )
                SELECT id FROM descendants
                """,
                [pk_str],
            )
            ids = [row[0] for row in cursor.fetchall()]
        return list(OrgUnit.objects.filter(pk__in=ids))


class Membership(models.Model):
    """Explicit membership of a User in an OrgUnit with a role."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    org_unit = models.ForeignKey(
        OrgUnit,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        app_label = "org"
        db_table = "memberships"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["user", "org_unit"], name="unique_user_org_unit"),
        ]

    def __str__(self) -> str:
        return f"{self.user} in {self.org_unit} ({self.role})"


class APIKey(models.Model):
    """An API key scoped to an OrgUnit for external integrations."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    prefix = models.CharField(max_length=8, db_index=True)
    hashed_key = models.CharField(max_length=64)
    org_unit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE, related_name="api_keys")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_api_keys",
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "org"
        db_table = "api_keys"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["prefix", "hashed_key"], name="unique_api_key"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.prefix}...)"
