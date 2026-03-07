from rest_framework_nested import routers

from app.org.views import APIKeyViewSet, MembershipViewSet, OrgUnitViewSet

router = routers.DefaultRouter()
router.register("units", OrgUnitViewSet, basename="org-unit")

units_router = routers.NestedDefaultRouter(router, "units", lookup="unit")
units_router.register("members", MembershipViewSet, basename="org-unit-members")
units_router.register("api-keys", APIKeyViewSet, basename="org-unit-api-keys")

urlpatterns = router.urls + units_router.urls
