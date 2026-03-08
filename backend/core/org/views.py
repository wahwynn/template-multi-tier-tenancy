from __future__ import annotations

import hashlib
import secrets

from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from core.org.models import APIKey, Membership, OrgUnit
from core.org.serializers import (
    APIKeyCreateSerializer,
    APIKeyListSerializer,
    MembershipSerializer,
    OrgUnitSerializer,
)


class OrgUnitCursorPagination(CursorPagination):
    ordering = "name"


class OrgUnitListCreateView(ListCreateAPIView):
    serializer_class = OrgUnitSerializer
    queryset = OrgUnit.objects.all()
    pagination_class = OrgUnitCursorPagination


class OrgUnitDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = OrgUnitSerializer
    queryset = OrgUnit.objects.all()


class MemberListCreateView(ListCreateAPIView):
    serializer_class = MembershipSerializer

    def get_queryset(self):
        return Membership.objects.filter(org_unit_id=self.kwargs["pk"])


class APIKeyListCreateView(APIView):
    def get(self, request, pk):
        keys = APIKey.objects.filter(org_unit_id=pk)
        return Response(APIKeyListSerializer(keys, many=True).data)

    def post(self, request, pk):
        raw_key = secrets.token_hex(32)
        prefix = raw_key[:8]
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()
        key = APIKey.objects.create(
            name=request.data.get("name", ""),
            prefix=prefix,
            hashed_key=hashed,
            org_unit_id=pk,
            role=request.data.get("role", "member"),
            created_by=request.user,
        )
        serializer = APIKeyCreateSerializer(key, context={"full_key": raw_key})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class APIKeyDeleteView(APIView):
    def delete(self, request, pk, kid):
        APIKey.objects.filter(pk=kid, org_unit_id=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
