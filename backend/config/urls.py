from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("v1/auth/token/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("v1/org/", include("app.org.urls")),
]
