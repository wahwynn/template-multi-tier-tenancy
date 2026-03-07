from rest_framework.authentication import BaseAuthentication


class APIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        return None
