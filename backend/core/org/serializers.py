from __future__ import annotations

from typing import ClassVar

from rest_framework import serializers

from core.org.models import APIKey, Membership, OrgUnit


class OrgUnitSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = OrgUnit
        fields: ClassVar = ["id", "name", "slug", "node_type", "isolation_policy", "parent", "children"]

    def get_children(self, obj: OrgUnit) -> list:
        return [{"id": str(c.pk), "name": c.name, "slug": c.slug} for c in obj.children.all()]


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields: ClassVar = ["id", "user", "org_unit", "role"]


class APIKeyCreateSerializer(serializers.ModelSerializer):
    """Write-only serializer — returns the full key once at creation."""

    full_key = serializers.SerializerMethodField()

    class Meta:
        model = APIKey
        fields: ClassVar = ["id", "name", "prefix", "role", "expires_at", "full_key"]
        read_only_fields: ClassVar = ["id", "prefix", "full_key"]

    def get_full_key(self, obj: APIKey) -> str | None:
        return self.context.get("full_key")


class APIKeyListSerializer(serializers.ModelSerializer):
    """Read-only serializer — never returns the full key."""

    class Meta:
        model = APIKey
        fields: ClassVar = ["id", "name", "prefix", "role", "expires_at", "last_used_at"]
