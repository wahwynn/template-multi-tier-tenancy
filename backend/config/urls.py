from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from app.org.jwt_views import EmailTokenObtainPairView

urlpatterns = [
    path("v1/auth/token/", EmailTokenObtainPairView.as_view(), name="token-obtain"),
    path("v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("v1/org/", include("app.org.urls")),
]
