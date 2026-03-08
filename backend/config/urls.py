from core.users.jwt_views import EmailTokenObtainPairView
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("v1/auth/token/", EmailTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("v1/org/", include("core.org.urls")),
]
