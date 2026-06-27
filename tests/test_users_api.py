"""
tests/test_users_api.py
========================
Full coverage for backend/api/users.py

- GET  /api/users/me
- PUT  /api/users/me
- DELETE /api/users/me
- GET  /api/users/{user_id}
- GET  /api/users/  (admin)
- PUT  /api/users/{user_id} (admin)
- DELETE /api/users/{user_id} (admin)
- POST /api/users/{user_id}/suspend (admin)
- POST /api/users/{user_id}/activate (admin)
"""

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars00")
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars01")
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth.jwt_handler import create_access_token
from backend.auth.user_service import UserCreate, UserService
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
def users_client(db_session):
    mock_redis = MagicMock()
    mock_redis.exists.return_value = 0
    mock_redis.setex.return_value = True

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch("backend.auth.jwt_handler.redis_client", mock_redis):
        client = TestClient(app, raise_server_exceptions=False)
        yield client, db_session, mock_redis

    app.dependency_overrides.pop(get_db, None)


# ── helpers ──────────────────────────────────────────────────────────────────


def _create_user(db_session, role="user"):
    svc = UserService(db_session)
    email = f"u_{uuid.uuid4().hex[:8]}@test.com"
    user = svc.create_user(UserCreate(email=email, password="TestPass1!", full_name="Test User"))
    user.role = role
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return user, token


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


# ── GET /api/users/me ─────────────────────────────────────────────────────────


class TestGetMe:
    def test_get_me_returns_own_profile(self, users_client):
        client, db, _ = users_client
        user, token = _create_user(db)
        resp = client.get("/api/users/me", headers=_headers(token))
        assert resp.status_code == 200
        assert resp.json()["email"] == user.email

    def test_get_me_no_auth_returns_401_or_403(self, users_client):
        client, _, _ = users_client
        resp = client.get("/api/users/me")
        assert resp.status_code in (401, 403)


# ── PUT /api/users/me ─────────────────────────────────────────────────────────


class TestUpdateMe:
    def test_update_me_full_name(self, users_client):
        client, db, _ = users_client
        user, token = _create_user(db)
        resp = client.put(
            "/api/users/me",
            json={"full_name": "Updated Name"},
            headers=_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Updated Name"

    def test_update_me_no_auth_returns_401_or_403(self, users_client):
        client, _, _ = users_client
        resp = client.put("/api/users/me", json={"full_name": "X"})
        assert resp.status_code in (401, 403)


# ── DELETE /api/users/me ──────────────────────────────────────────────────────


class TestDeleteMe:
    def test_delete_me_soft_deletes(self, users_client):
        client, db, _ = users_client
        user, token = _create_user(db)
        resp = client.delete("/api/users/me", headers=_headers(token))
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()


# ── GET /api/users/{user_id} ──────────────────────────────────────────────────


class TestGetUser:
    def test_user_can_get_own_profile(self, users_client):
        client, db, _ = users_client
        user, token = _create_user(db)
        resp = client.get(f"/api/users/{user.id}", headers=_headers(token))
        assert resp.status_code == 200

    def test_user_cannot_get_other_user_profile(self, users_client):
        client, db, _ = users_client
        user1, token1 = _create_user(db)
        user2, _ = _create_user(db)
        resp = client.get(f"/api/users/{user2.id}", headers=_headers(token1))
        assert resp.status_code == 403

    def test_admin_can_get_any_user(self, users_client):
        client, db, _ = users_client
        _, admin_token = _create_user(db, role="admin")
        target_user, _ = _create_user(db)
        resp = client.get(f"/api/users/{target_user.id}", headers=_headers(admin_token))
        assert resp.status_code == 200

    def test_get_nonexistent_user_returns_404(self, users_client):
        client, db, _ = users_client
        _, admin_token = _create_user(db, role="admin")
        resp = client.get("/api/users/nonexistent-uuid", headers=_headers(admin_token))
        assert resp.status_code == 404


# ── GET /api/users/ (admin) ────────────────────────────────────────────────────


class TestListUsers:
    def test_admin_can_list_users(self, users_client):
        client, db, _ = users_client
        _, admin_token = _create_user(db, role="admin")
        resp = client.get("/api/users/", headers=_headers(admin_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_non_admin_cannot_list_users(self, users_client):
        client, db, _ = users_client
        _, user_token = _create_user(db, role="user")
        resp = client.get("/api/users/", headers=_headers(user_token))
        assert resp.status_code == 403


# ── PUT /api/users/{user_id} (admin) ──────────────────────────────────────────


class TestAdminUpdateUser:
    def test_admin_can_update_user(self, users_client):
        client, db, _ = users_client
        _, admin_token = _create_user(db, role="admin")
        target, _ = _create_user(db)
        resp = client.put(
            f"/api/users/{target.id}",
            json={"full_name": "Admin Updated"},
            headers=_headers(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Admin Updated"

    def test_admin_update_nonexistent_returns_404(self, users_client):
        client, db, _ = users_client
        _, admin_token = _create_user(db, role="admin")
        resp = client.put(
            "/api/users/does-not-exist",
            json={"full_name": "X"},
            headers=_headers(admin_token),
        )
        assert resp.status_code == 404


# ── DELETE /api/users/{user_id} (admin) ───────────────────────────────────────


class TestAdminDeleteUser:
    def test_admin_can_delete_user(self, users_client):
        client, db, _ = users_client
        _, admin_token = _create_user(db, role="admin")
        target, _ = _create_user(db)
        resp = client.delete(f"/api/users/{target.id}", headers=_headers(admin_token))
        assert resp.status_code == 200

    def test_admin_delete_nonexistent_returns_404(self, users_client):
        client, db, _ = users_client
        _, admin_token = _create_user(db, role="admin")
        resp = client.delete("/api/users/does-not-exist", headers=_headers(admin_token))
        assert resp.status_code == 404

    def test_non_admin_cannot_delete_user(self, users_client):
        client, db, _ = users_client
        target, _ = _create_user(db)
        _, user_token = _create_user(db, role="user")
        resp = client.delete(f"/api/users/{target.id}", headers=_headers(user_token))
        assert resp.status_code == 403


# ── POST /api/users/{user_id}/suspend ─────────────────────────────────────────


class TestSuspendActivate:
    def test_admin_can_suspend_user(self, users_client):
        client, db, _ = users_client
        _, admin_token = _create_user(db, role="admin")
        target, _ = _create_user(db)
        resp = client.post(f"/api/users/{target.id}/suspend", headers=_headers(admin_token))
        assert resp.status_code == 200

    def test_suspend_nonexistent_returns_404(self, users_client):
        client, db, _ = users_client
        _, admin_token = _create_user(db, role="admin")
        resp = client.post("/api/users/ghost-id/suspend", headers=_headers(admin_token))
        assert resp.status_code == 404

    def test_admin_can_activate_user(self, users_client):
        client, db, _ = users_client
        _, admin_token = _create_user(db, role="admin")
        target, _ = _create_user(db)
        # Suspend first
        client.post(f"/api/users/{target.id}/suspend", headers=_headers(admin_token))
        # Then activate
        resp = client.post(f"/api/users/{target.id}/activate", headers=_headers(admin_token))
        assert resp.status_code == 200

    def test_activate_nonexistent_returns_404(self, users_client):
        client, db, _ = users_client
        _, admin_token = _create_user(db, role="admin")
        resp = client.post("/api/users/ghost-id/activate", headers=_headers(admin_token))
        assert resp.status_code == 404

    def test_non_admin_cannot_suspend(self, users_client):
        client, db, _ = users_client
        target, _ = _create_user(db)
        _, user_token = _create_user(db, role="user")
        resp = client.post(f"/api/users/{target.id}/suspend", headers=_headers(user_token))
        assert resp.status_code == 403
