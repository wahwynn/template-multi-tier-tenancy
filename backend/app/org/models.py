"""Org hierarchy models.

OrgUnit is a self-referential tree node representing any level of
organisational structure (org, department, team, franchise, etc.).

Isolation policy controls data visibility across parent/child boundaries:
- open:         parent sees in, child sees parent (default)
- isolated:     neither direction crosses the boundary
- inherit_only: child sees parent, parent cannot see in
- visible_only: parent sees in, child cannot see parent
"""

from __future__ import annotations

import uuid
from typing import ClassVar

from django.contrib.auth import get_user_model
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
        app_label = "app_org"

    def __str__(self) -> str:
        return self.name

    def get_ancestors(self) -> list[OrgUnit]:
        """Return list of ancestors from immediate parent to root."""
        ancestors: list[OrgUnit] = []
        current = self.parent
        while current is not None:
            ancestors.append(current)
            current = current.parent
        return ancestors

    def get_descendants(self) -> list[OrgUnit]:
        """Return all descendant nodes via recursive CTE."""
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH RECURSIVE descendants AS (
                    SELECT id FROM app_org_orgunit WHERE parent_id = %s
                    UNION ALL
                    SELECT o.id FROM app_org_orgunit o
                    INNER JOIN descendants d ON o.parent_id = d.id
                )
                SELECT id FROM descendants
                """,
                [str(self.pk)],
            )
            ids = [row[0] for row in cursor.fetchall()]
        return list(OrgUnit.objects.filter(pk__in=ids))


class Membership(models.Model):
    """Explicit membership of a User in an OrgUnit with a role."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        get_user_model(),
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
        app_label = "app_org"
        constraints: ClassVar = [models.UniqueConstraint(fields=["user", "org_unit"], name="unique_user_org_unit")]

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
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_api_keys",
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "app_org"
        constraints: ClassVar = [models.UniqueConstraint(fields=["prefix", "hashed_key"], name="unique_api_key")]

    def __str__(self) -> str:
        return f"{self.name} ({self.prefix}...)"
