"""
Tests d'authentification JWT.
"""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestJWTAuth:
    def test_obtain_token_success(self, client, user):
        """Credentials valides → access + refresh tokens."""
        response = client.post("/api/auth/token/", {
            "username": "testuser",
            "password": "testpass123",
        })
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_obtain_token_wrong_password(self, client, user):
        response = client.post("/api/auth/token/", {
            "username": "testuser",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    def test_obtain_token_unknown_user(self, client):
        response = client.post("/api/auth/token/", {
            "username": "nobody",
            "password": "nopass",
        })
        assert response.status_code == 401

    def test_refresh_token_success(self, client, user):
        """Refresh token valide → nouveau access token."""
        obtain = client.post("/api/auth/token/", {
            "username": "testuser",
            "password": "testpass123",
        })
        refresh_token = obtain.data["refresh"]
        response = client.post("/api/auth/token/refresh/", {"refresh": refresh_token})
        assert response.status_code == 200
        assert "access" in response.data

    def test_refresh_token_invalid(self, client):
        response = client.post("/api/auth/token/refresh/", {"refresh": "notavalidtoken"})
        assert response.status_code == 401

    def test_access_protected_without_token(self, client):
        """Sans token → 401 sur un endpoint protégé."""
        response = client.get("/api/parcels/")
        assert response.status_code == 401

    def test_access_protected_with_valid_token(self, client, user):
        """Avec token valide → 200."""
        obtain = client.post("/api/auth/token/", {
            "username": "testuser",
            "password": "testpass123",
        })
        access = obtain.data["access"]
        response = client.get("/api/parcels/", HTTP_AUTHORIZATION=f"Bearer {access}")
        assert response.status_code == 200

    def test_access_with_malformed_token(self, client):
        response = client.get("/api/parcels/", HTTP_AUTHORIZATION="Bearer not.a.jwt")
        assert response.status_code == 401

    def test_register_creates_user(self, client):
        """POST /api/auth/register/ crée un user et retourne 201."""
        response = client.post("/api/auth/register/", {
            "username": "newuser",
            "password": "StrongPass123!",
            "email": "new@test.com",
        })
        assert response.status_code == 201
        assert User.objects.filter(username="newuser").exists()

    def test_register_duplicate_username(self, client, user):
        """Username déjà pris → 400."""
        response = client.post("/api/auth/register/", {
            "username": "testuser",
            "password": "AnotherPass456!",
            "email": "dup@test.com",
        })
        assert response.status_code == 400
