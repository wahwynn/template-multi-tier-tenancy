"""DRF serializers for org hierarchy models."""

from __future__ import annotations

import hashlib
import secrets

from rest_framework import serializers

from app.org.models import APIKey, Membership, OrgUnit


class OrgUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgUnit
        fields = ["id", "name", "slug", "parent", "node_type", "isolation_policy"]


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ["id", "user", "org_unit", "role"]


class APIKeyCreateSerializer(serializers.ModelSerializer):
    """Used only on creation — returns the full raw key once."""

    raw_key = serializers.CharField(read_only=True)

    class Meta:
        model = APIKey
        fields = ["id", "name", "org_unit", "role", "expires_at", "raw_key"]


class APIKeyListSerializer(serializers.ModelSerializer):
    """Safe for listing — never exposes the key."""

    class Meta:
        model = APIKey
        fields = ["id", "name", "prefix", "org_unit", "role", "expires_at", "last_used_at"]
