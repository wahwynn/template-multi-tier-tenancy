"""Tests for custom exception handler."""

from django.core.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.test import APIRequestFactory

from core.tenants.exceptions import custom_exception_handler


def test_custom_exception_handler_formats_drf_exception():
    factory = APIRequestFactory()
    request = factory.get("/")
    exc = NotFound("resource not found")
    response = custom_exception_handler(exc, {"request": request})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data == {"error": {"code": "not_found", "message": "resource not found"}}


def test_custom_exception_handler_returns_none_for_unknown():
    response = custom_exception_handler(ValueError("oops"), {})
    assert response is None
