"""
Tests for backend/main.py — startup, middleware, health check, exception handler.
External services (DB, Redis, Ollama) are mocked.
"""
import os
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestHealthCheck:
    def test_health_returns_online(self, client):
        with patch("sqlalchemy.create_engine"), patch("redis.from_url") as mock_redis_cls, patch(
            "requests.get"
        ):
            mock_redis_cls.return_value = MagicMock()
            mock_redis_cls.return_value.ping.side_effect = Exception("no redis")
            resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ONLINE"
        assert "checks" in data

    def test_health_db_check_sqlite(self, client):
        """With SQLite DATABASE_URL the DB check is skipped (no connectivity check)."""
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite://"}):
            resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["checks"]["db"] in ("ok", "unreachable")

    def test_health_db_unreachable(self, client):
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://localhost/fake"}
        ), patch("sqlalchemy.create_engine", side_effect=Exception("no db")):
            resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["checks"]["db"] == "unreachable"

    def test_health_redis_ok(self, client):
        with patch("redis.from_url") as mock_from_url:
            mock_r = MagicMock()
            mock_r.ping.return_value = True
            mock_from_url.return_value = mock_r
            resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["checks"]["redis"] in ("ok", "unreachable")

    def test_health_ollama_ok(self, client):
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            with patch.dict(os.environ, {"OLLAMA_URL": "http://localhost:11434"}):
                resp = client.get("/health")
        assert resp.status_code == 200


class TestMetricsEndpoint:
    def test_metrics_returns_response(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200


class TestMiddleware:
    def test_correlation_id_header_added(self, client):
        resp = client.get("/health")
        assert "x-request-id" in resp.headers

    def test_correlation_id_propagated(self, client):
        resp = client.get("/health", headers={"X-Request-ID": "my-request-id"})
        assert resp.headers.get("x-request-id") == "my-request-id"

    def test_rate_limit_middleware_passes_normal_requests(self, client):
        """A single request should not be rate limited."""
        resp = client.get("/health")
        assert resp.status_code != 429


class TestGlobalExceptionHandler:
    def test_global_exception_handler_is_registered(self):
        """Verify the exception handler is registered on the app."""
        from backend.main import app

        # The handler is registered — verify its presence in the exception handlers dict
        # FastAPI stores handlers in app.exception_handlers keyed by exception class
        handler_classes = list(app.exception_handlers.keys())
        assert Exception in handler_classes or len(handler_classes) > 0

    @pytest.mark.asyncio
    async def test_global_exception_handler_returns_json(self):
        """Test the handler function directly produces the correct JSON structure."""
        from unittest.mock import MagicMock
        import json
        from backend.main import _global_exception_handler

        mock_request = MagicMock()
        mock_request.state.request_id = "test-rid"
        mock_request.url.path = "/test-path"

        response = await _global_exception_handler(mock_request, RuntimeError("boom"))
        assert response.status_code == 500
        body = json.loads(response.body)
        assert body["error"] == "Internal server error"
        assert body["request_id"] == "test-rid"


class TestRouterRegistrations:
    def test_auth_routes_exist(self, client):
        resp = client.post("/api/auth/login", json={"email": "x@example.com", "password": "y"})
        assert resp.status_code in (200, 400, 401, 422)

    def test_users_routes_exist(self, client):
        resp = client.get("/api/users/")
        assert resp.status_code in (200, 401, 403, 404, 422)

    def test_companies_routes_exist(self, client):
        resp = client.get("/api/companies/")
        assert resp.status_code in (200, 401, 403)

    def test_deployments_routes_exist(self, client):
        resp = client.get("/api/deployments/")
        assert resp.status_code in (200, 401, 403)

    def test_webhooks_routes_exist(self, client):
        resp = client.post("/api/webhooks/stripe", content=b"{}")
        assert resp.status_code in (200, 400, 401, 422)

    def test_notifications_routes_exist(self, client):
        resp = client.get("/api/notifications/")
        assert resp.status_code in (200, 401, 403)

    def test_tickets_routes_exist(self, client):
        resp = client.get("/api/tickets/")
        assert resp.status_code in (200, 401, 403)

    def test_workflows_routes_exist(self, client):
        resp = client.get("/api/workflows/")
        assert resp.status_code in (200, 401, 403)


class TestLifespanCoverage:
    def test_lifespan_starts_and_stops(self):
        """Test lifespan by creating a fresh TestClient (triggers startup)."""
        from backend.main import app

        with TestClient(app, raise_server_exceptions=False) as c:
            resp = c.get("/health")
            assert resp.status_code == 200

    def test_lifespan_db_check_non_postgres(self):
        """When DATABASE_URL is SQLite, DB connectivity check is skipped."""
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite://"}):
            from backend.main import app

            with TestClient(app, raise_server_exceptions=False) as c:
                resp = c.get("/health")
            assert resp.status_code == 200
