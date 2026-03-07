"""API views for the org hierarchy."""

from __future__ import annotations

import hashlib
import secrets
from typing import TYPE_CHECKING, ClassVar

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

if TYPE_CHECKING:
    from rest_framework.request import Request

from app.org.models import APIKey, Membership, OrgUnit
from app.org.serializers import (
    APIKeyCreateSerializer,
    APIKeyListSerializer,
    MembershipSerializer,
    OrgUnitSerializer,
)


class OrgUnitPagination(CursorPagination):
    ordering = "id"
    page_size = 50


class MembershipPagination(CursorPagination):
    ordering = "id"
    page_size = 50


class OrgUnitViewSet(ModelViewSet):
    serializer_class = OrgUnitSerializer
    pagination_class = OrgUnitPagination

    def _member_unit_ids(self):
        return Membership.objects.filter(user=self.request.user).values_list("org_unit_id", flat=True)

    def get_queryset(self):
        return OrgUnit.objects.filter(pk__in=self._member_unit_ids())

    def _accessible_queryset(self):
        """Broader queryset: member units plus all their descendants."""
        from django.db import connection

        member_ids = list(self._member_unit_ids())
        if not member_ids:
            return OrgUnit.objects.none()

        placeholders = ", ".join(["%s"] * len(member_ids))
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                WITH RECURSIVE tree AS (
                    SELECT id FROM app_org_orgunit WHERE id IN ({placeholders})
                    UNION ALL
                    SELECT o.id FROM app_org_orgunit o
                    INNER JOIN tree t ON o.parent_id = t.id
                )
                SELECT id FROM tree
                """,
                [str(i) for i in member_ids],
            )
            ids = [row[0] for row in cursor.fetchall()]
        return OrgUnit.objects.filter(pk__in=ids)

    @action(detail=True, methods=["get"])
    def ancestors(self, request: Request, pk=None) -> Response:
        queryset = self._accessible_queryset()
        unit = queryset.get(pk=pk)
        serializer = OrgUnitSerializer(unit.get_ancestors(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def descendants(self, request: Request, pk=None) -> Response:
        unit = self.get_object()
        serializer = OrgUnitSerializer(unit.get_descendants(), many=True)
        return Response(serializer.data)


class MembershipViewSet(ModelViewSet):
    serializer_class = MembershipSerializer
    pagination_class = MembershipPagination

    def get_queryset(self):
        return Membership.objects.filter(org_unit_id=self.kwargs["unit_pk"])


class APIKeyViewSet(ModelViewSet):
    http_method_names: ClassVar = ["get", "post", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return APIKeyCreateSerializer
        return APIKeyListSerializer

    def get_queryset(self):
        return APIKey.objects.filter(org_unit_id=self.kwargs["unit_pk"])

    def create(self, request: Request, unit_pk=None) -> Response:
        raw_key = secrets.token_hex(32)
        prefix = raw_key[:8]
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()

        serializer = APIKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = serializer.save(
            prefix=prefix,
            hashed_key=hashed,
            created_by=request.user,
            org_unit_id=unit_pk,
        )
        data = APIKeyCreateSerializer(key).data
        data["raw_key"] = raw_key
        return Response(data, status=status.HTTP_201_CREATED)
