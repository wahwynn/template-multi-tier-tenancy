from django.urls import path

from core.org.views import (
    APIKeyDeleteView,
    APIKeyListCreateView,
    MemberListCreateView,
    OrgUnitDetailView,
    OrgUnitListCreateView,
)

urlpatterns = [
    path("units/", OrgUnitListCreateView.as_view(), name="org-unit-list"),
    path("units/<uuid:pk>/", OrgUnitDetailView.as_view(), name="org-unit-detail"),
    path("units/<uuid:pk>/members/", MemberListCreateView.as_view(), name="org-unit-members"),
    path("units/<uuid:pk>/api-keys/", APIKeyListCreateView.as_view(), name="org-unit-api-keys"),
    path("units/<uuid:pk>/api-keys/<uuid:kid>/", APIKeyDeleteView.as_view(), name="org-unit-api-key-delete"),
]
