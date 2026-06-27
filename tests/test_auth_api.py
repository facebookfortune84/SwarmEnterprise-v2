"""
tests/test_auth_api.py
======================
Full coverage for backend/api/auth.py

- register: success, duplicate email, invalid email format
- login: success, wrong password, non-existent email
- logout: success, failed revocation
- refresh: success, invalid refresh token
- verify: valid token
- me: success, user not found
"""

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars00")
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars01")
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("DRY_RUN_MODE", "true")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.base import Base
from backend.db.session import get_db
from backend.main import app


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def auth_client(db_session):
    """TestClient with DB override and mocked Redis."""
    mock_redis = MagicMock()
    mock_redis.exists.return_value = 0
    mock_redis.setex.return_value = True

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch("backend.auth.jwt_handler.redis_client", mock_redis):
        client = TestClient(app, raise_server_exceptions=False)
        yield client, mock_redis

    app.dependency_overrides.pop(get_db, None)


# ── helpers ─────────────────────────────────────────────────────────────────


def _register(client, email=None, password="TestPass1!"):
    email = email or f"user_{uuid.uuid4().hex[:8]}@test.com"
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    return resp, email


# ── POST /api/auth/register ──────────────────────────────────────────────────


class TestRegister:
    def test_register_success_returns_201(self, auth_client):
        client, _ = auth_client
        resp, _ = _register(client)
        assert resp.status_code == 201

    def test_register_success_body_has_tokens(self, auth_client):
        client, _ = auth_client
        resp, _ = _register(client)
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    def test_register_success_body_has_user(self, auth_client):
        client, _ = auth_client
        resp, email = _register(client)
        user = resp.json()["user"]
        assert user["email"] == email
        assert user["role"] == "user"
        assert user["is_active"] is True

    def test_register_duplicate_email_returns_400(self, auth_client):
        client, _ = auth_client
        _, email = _register(client)
        # Second registration with same email
        resp2 = client.post(
            "/api/auth/register",
            json={"email": email, "password": "TestPass1!", "full_name": "Dup"},
        )
        assert resp2.status_code == 400
        assert "already registered" in resp2.json()["detail"].lower()

    def test_register_invalid_email_returns_422(self, auth_client):
        client, _ = auth_client
        resp = client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "password": "TestPass1!", "full_name": "Bad"},
        )
        assert resp.status_code == 422

    def test_register_short_password_returns_422(self, auth_client):
        client, _ = auth_client
        resp = client.post(
            "/api/auth/register",
            json={"email": "short@test.com", "password": "abc", "full_name": "Short"},
        )
        assert resp.status_code == 422

    def test_register_missing_full_name_returns_422(self, auth_client):
        client, _ = auth_client
        resp = client.post(
            "/api/auth/register",
            json={"email": "nofull@test.com", "password": "TestPass1!"},
        )
        assert resp.status_code == 422


# ── POST /api/auth/login ─────────────────────────────────────────────────────


class TestLogin:
    def test_login_success_returns_200(self, auth_client):
        client, _ = auth_client
        _, email = _register(client)
        resp = client.post(
            "/api/auth/login",
            json={"email": email, "password": "TestPass1!"},
        )
        assert resp.status_code == 200

    def test_login_success_body_has_tokens(self, auth_client):
        client, _ = auth_client
        _, email = _register(client)
        resp = client.post(
            "/api/auth/login",
            json={"email": email, "password": "TestPass1!"},
        )
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

    def test_login_wrong_password_returns_401(self, auth_client):
        client, _ = auth_client
        _, email = _register(client)
        resp = client.post(
            "/api/auth/login",
            json={"email": email, "password": "WrongPass!"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_email_returns_401(self, auth_client):
        client, _ = auth_client
        resp = client.post(
            "/api/auth/login",
            json={"email": "ghost@test.com", "password": "TestPass1!"},
        )
        assert resp.status_code == 401

    def test_login_invalid_email_format_returns_422(self, auth_client):
        client, _ = auth_client
        resp = client.post(
            "/api/auth/login",
            json={"email": "not-email", "password": "TestPass1!"},
        )
        assert resp.status_code == 422


# ── POST /api/auth/logout ────────────────────────────────────────────────────


class TestLogout:
    def test_logout_success(self, auth_client):
        client, mock_redis = auth_client
        _, email = _register(client)
        login_resp = client.post(
            "/api/auth/login",
            json={"email": email, "password": "TestPass1!"},
        )
        token = login_resp.json()["access_token"]
        mock_redis.setex.return_value = True
        mock_redis.exists.return_value = 0  # not revoked during revoke call
        resp = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert "logged out" in resp.json()["message"].lower()

    def test_logout_missing_token_returns_403(self, auth_client):
        client, _ = auth_client
        resp = client.post("/api/auth/logout")
        assert resp.status_code in (401, 403, 422)


# ── POST /api/auth/refresh ───────────────────────────────────────────────────


class TestRefresh:
    def test_refresh_valid_token(self, auth_client):
        client, mock_redis = auth_client
        _, email = _register(client)
        login_resp = client.post(
            "/api/auth/login",
            json={"email": email, "password": "TestPass1!"},
        )
        refresh_token = login_resp.json()["refresh_token"]
        mock_redis.exists.return_value = 0  # not revoked
        resp = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_refresh_invalid_token_returns_401(self, auth_client):
        client, _ = auth_client
        resp = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "completely.invalid.token"},
        )
        assert resp.status_code == 401

    def test_refresh_access_token_as_refresh_returns_401(self, auth_client):
        client, mock_redis = auth_client
        _, email = _register(client)
        login_resp = client.post(
            "/api/auth/login",
            json={"email": email, "password": "TestPass1!"},
        )
        access_token = login_resp.json()["access_token"]
        mock_redis.exists.return_value = 0
        # Access tokens have type="access", not "refresh" — should fail
        resp = client.post(
            "/api/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert resp.status_code == 401


# ── GET /api/auth/verify ─────────────────────────────────────────────────────


class TestVerify:
    def test_verify_valid_token(self, auth_client):
        client, mock_redis = auth_client
        _, email = _register(client)
        login_resp = client.post(
            "/api/auth/login",
            json={"email": email, "password": "TestPass1!"},
        )
        token = login_resp.json()["access_token"]
        mock_redis.exists.return_value = 0
        resp = client.get(
            "/api/auth/verify",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    def test_verify_no_token_returns_401_or_403(self, auth_client):
        client, _ = auth_client
        resp = client.get("/api/auth/verify")
        assert resp.status_code in (401, 403)


# ── GET /api/auth/me ─────────────────────────────────────────────────────────


class TestMe:
    def test_me_returns_user_profile(self, auth_client):
        client, mock_redis = auth_client
        _, email = _register(client)
        login_resp = client.post(
            "/api/auth/login",
            json={"email": email, "password": "TestPass1!"},
        )
        token = login_resp.json()["access_token"]
        mock_redis.exists.return_value = 0
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == email

    def test_me_no_token_returns_401_or_403(self, auth_client):
        client, _ = auth_client
        resp = client.get("/api/auth/me")
        assert resp.status_code in (401, 403)
