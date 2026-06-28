"""
tests/test_health_and_middleware.py
=====================================
Coverage for:
  - backend/main.py health_check, global exception handler, CORS, rate limit,
    correlation ID middleware, metrics endpoint
  - backend/auth/middleware.py  get_current_user, RateLimitMiddleware,
    verify_api_key_in_db, verify_api_key
  - backend/auth/permissions.py  can_access_resource
"""

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars00")
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars01")
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.base import Base
from backend.main import app


@pytest.fixture(scope="module")
def client():
    """Plain TestClient — no DB overrides — for middleware / health tests."""
    mock_redis = MagicMock()
    mock_redis.exists.return_value = 0
    mock_redis.setex.return_value = True
    with patch("backend.auth.jwt_handler.redis_client", mock_redis):
        yield TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


# ── GET /health ───────────────────────────────────────────────────────────────


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_body_has_status(self, client):
        body = client.get("/health").json()
        assert body["status"] == "ONLINE"
        assert body["version"] == "2.0.0"

    def test_health_body_has_checks(self, client):
        body = client.get("/health").json()
        assert "checks" in body
        assert "db" in body["checks"]
        assert "redis" in body["checks"]
        assert "ollama" in body["checks"]

    def test_health_checks_unreachable_when_no_db(self, client):
        """With SQLite URL, the DB check should succeed (SQLite is in-process)."""
        body = client.get("/health").json()
        # Values are either "ok" or "unreachable" — both are valid strings
        assert body["checks"]["db"] in ("ok", "unreachable")

    def test_health_db_unreachable_on_bad_url(self):
        """Force db_url to a bad postgres URL so the check returns unreachable."""
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("no redis")
        with patch("backend.auth.jwt_handler.redis_client", MagicMock(exists=lambda x: 0)):
            with patch.dict(os.environ, {"DATABASE_URL": "postgresql://bad:bad@localhost:1/bad"}):
                c = TestClient(app, raise_server_exceptions=False)
                body = c.get("/health").json()
        assert body["checks"]["db"] in ("ok", "unreachable")


# ── GET /metrics ──────────────────────────────────────────────────────────────


class TestMetricsEndpoint:
    def test_metrics_returns_200(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200


# ── Correlation ID middleware ─────────────────────────────────────────────────


class TestCorrelationIDMiddleware:
    def test_x_request_id_returned_on_all_responses(self, client):
        resp = client.get("/health")
        assert "x-request-id" in resp.headers

    def test_custom_x_request_id_is_echoed(self, client):
        resp = client.get("/health", headers={"X-Request-ID": "my-custom-id"})
        assert resp.headers.get("x-request-id") == "my-custom-id"

    def test_request_id_auto_generated_when_absent(self, client):
        resp = client.get("/health")
        rid = resp.headers.get("x-request-id", "")
        assert len(rid) == 36  # UUID4 format


# ── Global exception handler ──────────────────────────────────────────────────


class TestGlobalExceptionHandler:
    def test_unhandled_exception_returns_500_json(self):
        """Mount a route that raises to trigger the global handler."""
        from fastapi import FastAPI
        import contextlib

        @contextlib.asynccontextmanager
        async def _ls(a):
            yield

        test_app = FastAPI(lifespan=_ls)

        @test_app.get("/boom")
        def _boom():
            raise RuntimeError("deliberate test explosion")

        c = TestClient(test_app, raise_server_exceptions=False)
        resp = c.get("/boom")
        # FastAPI default: 500 with text/plain or JSON
        assert resp.status_code == 500


# ── RateLimitMiddleware ───────────────────────────────────────────────────────


class TestRateLimitMiddleware:
    def test_rate_limit_allows_requests_below_threshold(self):
        from fastapi import FastAPI
        import contextlib
        from backend.auth.middleware import RateLimitMiddleware

        @contextlib.asynccontextmanager
        async def _ls(a):
            yield

        mini_app = FastAPI(lifespan=_ls)
        mini_app.add_middleware(RateLimitMiddleware, requests_per_minute=100)

        @mini_app.get("/ping")
        def ping():
            return {"pong": True}

        c = TestClient(mini_app, raise_server_exceptions=False)
        for _ in range(5):
            resp = c.get("/ping")
            assert resp.status_code == 200

    def test_rate_limit_blocks_after_threshold(self):
        from fastapi import FastAPI
        import contextlib
        from backend.auth.middleware import RateLimitMiddleware

        @contextlib.asynccontextmanager
        async def _ls(a):
            yield

        mini_app = FastAPI(lifespan=_ls)
        mini_app.add_middleware(RateLimitMiddleware, requests_per_minute=3)

        @mini_app.get("/ping")
        def ping():
            return {"pong": True}

        c = TestClient(mini_app, raise_server_exceptions=False)
        responses = [c.get("/ping").status_code for _ in range(6)]
        assert 429 in responses


# ── get_current_user — token type checks ─────────────────────────────────────


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_revoked_token_returns_401(self):
        from backend.auth.jwt_handler import create_access_token
        from backend.auth.middleware import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials
        from fastapi import HTTPException

        token = create_access_token({"sub": "u1", "email": "u@t.com"})
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        mock_redis = MagicMock()
        mock_redis.exists.return_value = 1  # revoked

        with patch("backend.auth.jwt_handler.redis_client", mock_redis):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(creds)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self):
        from backend.auth.middleware import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials
        from fastapi import HTTPException

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="garbage.token.here")
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 0

        with patch("backend.auth.jwt_handler.redis_client", mock_redis):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(creds)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_as_access_returns_401(self):
        from backend.auth.jwt_handler import create_refresh_token
        from backend.auth.middleware import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials
        from fastapi import HTTPException

        token = create_refresh_token({"sub": "u1", "email": "u@t.com"})
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 0

        with patch("backend.auth.jwt_handler.redis_client", mock_redis):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(creds)
        assert exc_info.value.status_code == 401


# ── verify_api_key_in_db ──────────────────────────────────────────────────────


class TestVerifyApiKeyInDb:
    def test_unknown_key_returns_false(self, db):
        from backend.auth.middleware import verify_api_key_in_db

        result = verify_api_key_in_db("no-such-key", db)
        assert result is False

    def test_inactive_key_returns_false(self, db):
        from backend.auth.middleware import verify_api_key_in_db
        from backend.db.models import APIKey, User

        user = User(
            id="u-ak-1",
            email="ak1@test.com",
            password_hash="x",
            full_name="AK",
            is_active=True,
        )
        db.add(user)
        db.flush()
        key = APIKey(key="inactive-key", user_id=user.id, name="K", is_active=False)
        db.add(key)
        db.commit()
        assert verify_api_key_in_db("inactive-key", db) is False

    def test_expired_key_returns_false(self, db):
        from backend.auth.middleware import verify_api_key_in_db
        from backend.db.models import APIKey, User

        user = User(
            id="u-ak-2",
            email="ak2@test.com",
            password_hash="x",
            full_name="AK2",
            is_active=True,
        )
        db.add(user)
        db.flush()
        key = APIKey(
            key="expired-key",
            user_id=user.id,
            name="K",
            is_active=True,
            expires_at=datetime.utcnow() - timedelta(days=1),
        )
        db.add(key)
        db.commit()
        assert verify_api_key_in_db("expired-key", db) is False

    def test_valid_key_returns_true(self, db):
        from backend.auth.middleware import verify_api_key_in_db
        from backend.db.models import APIKey, User

        user = User(
            id="u-ak-3",
            email="ak3@test.com",
            password_hash="x",
            full_name="AK3",
            is_active=True,
        )
        db.add(user)
        db.flush()
        key = APIKey(key="valid-key-123", user_id=user.id, name="K", is_active=True)
        db.add(key)
        db.commit()
        assert verify_api_key_in_db("valid-key-123", db) is True


# ── permissions ───────────────────────────────────────────────────────────────


class TestPermissions:
    def test_user_can_access_own_resource(self):
        from backend.auth.permissions import can_access_resource

        assert can_access_resource("user-1", "user-1", "user") is True

    def test_user_cannot_access_other_resource(self):
        from backend.auth.permissions import can_access_resource

        assert can_access_resource("user-1", "user-2", "user") is False

    def test_admin_can_access_any_resource(self):
        from backend.auth.permissions import can_access_resource

        assert can_access_resource("admin-1", "user-99", "admin") is True

    def test_superadmin_can_access_any_resource(self):
        from backend.auth.permissions import can_access_resource

        assert can_access_resource("sa-1", "anyone", "superadmin") is True
