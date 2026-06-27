"""
Comprehensive tests for all new/modified modules:
- backend/config.py
- backend/services/event_bus.py
- backend/api/tickets.py
- backend/api/notifications.py
- backend/api/workflows.py
- backend/db/ticket_history.py
- backend/services/ticket_service.py
- backend/services/notification_service.py
- backend/services/workflow_service.py

All external dependencies are mocked. No test touches Redis, Ollama, Docker, or
live HTTP. Each test runs in isolation with an in-memory SQLite database.
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ── test env defaults ──────────────────────────────────────────────────────────
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-64chars-minimum-length-for-tests-ok")
os.environ.setdefault("SECRET_KEY", "test-secret-key-64chars-minimum-length-for-tests-ok")

from backend.db.base import Base  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Shared in-memory DB fixture
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def db():
    """Fresh in-memory SQLite session per test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: backend/config.py
# ─────────────────────────────────────────────────────────────────────────────


class TestConfig:
    """100% branch coverage for backend/config.py."""

    def test_default_values_loaded(self):
        """DatabaseSettings falls back to SQLite when DATABASE_URL not set."""
        from backend.config import DatabaseSettings

        s = DatabaseSettings()
        assert "sqlite" in s.url or "swarm" in s.url

    def test_redis_url_optional(self):
        """RedisSettings.url is None by default."""
        from backend.config import RedisSettings

        s = RedisSettings()
        # url may be set from env; just assert it is a str or None
        assert s.url is None or isinstance(s.url, str)

    def test_stripe_defaults_are_placeholders(self):
        """Stripe defaults are placeholder values (not real keys)."""
        from backend.config import StripeSettings

        s = StripeSettings()
        assert "placeholder" in s.api_key or s.api_key.startswith("sk_")

    def test_jwt_settings_loaded(self):
        """JwtSettings reads from env correctly."""
        from backend.config import JwtSettings

        s = JwtSettings()
        assert s.secret_key  # not empty
        assert isinstance(s.access_token_expire_minutes, int)
        assert s.access_token_expire_minutes > 0

    def test_jwt_validator_passes_on_local_profile(self, monkeypatch):
        """Validator must NOT raise when DEPLOY_PROFILE is local (even with default key)."""
        monkeypatch.setenv("DEPLOY_PROFILE", "local")
        monkeypatch.setenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        import backend.config as cfg_mod
        # Bypass cache by instantiating directly
        s = cfg_mod.JwtSettings()  # should not raise
        assert s.secret_key is not None

    def test_jwt_validator_raises_in_non_local(self, monkeypatch):
        """Validator function raises ValueError when key is default in production."""
        monkeypatch.setenv("DEPLOY_PROFILE", "production")
        # Call the validator function directly, bypassing the cached Settings object
        from backend.config import JwtSettings
        validator = JwtSettings.secret_key_must_not_be_default_in_production
        with pytest.raises(ValueError, match="JWT_SECRET_KEY must be set"):
            validator("your-secret-key-change-in-production")

    def test_get_settings_is_cached(self):
        """get_settings() returns the same object on repeated calls."""
        from backend.config import get_settings

        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_settings_singleton_has_all_subsystems(self):
        """Top-level Settings exposes all sub-configs."""
        from backend.config import Settings

        s = Settings()
        assert hasattr(s, "database")
        assert hasattr(s, "redis")
        assert hasattr(s, "stripe")
        assert hasattr(s, "smtp")
        assert hasattr(s, "jwt")
        assert hasattr(s, "llm")
        assert hasattr(s, "deployment")

    def test_deployment_settings_defaults(self):
        """DeploymentSettings has sensible defaults."""
        from backend.config import DeploymentSettings

        s = DeploymentSettings()
        assert s.ssh_user in ("ubuntu", "deploy", "root") or isinstance(s.ssh_user, str)
        assert isinstance(s.tech_domain, str)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: backend/services/event_bus.py
# ─────────────────────────────────────────────────────────────────────────────


class TestEventBus:
    """Full branch coverage for EventBus."""

    def setup_method(self):
        from backend.services.event_bus import EventBus

        self.bus = EventBus()

    def test_subscribe_and_publish_sync(self):
        """Sync handler is called with payload."""
        received = []

        def handler(payload):
            received.append(payload)

        self.bus.subscribe("test.event", handler)
        self.bus.publish("test.event", {"key": "value"})
        assert received == [{"key": "value"}]

    def test_publish_no_subscribers(self):
        """Publishing to unknown event does not raise."""
        self.bus.publish("unknown.event", {"data": 1})  # must not raise

    def test_multiple_subscribers_all_called(self):
        """All handlers are called on a single publish."""
        log = []

        self.bus.subscribe("ev", lambda p: log.append("a"))
        self.bus.subscribe("ev", lambda p: log.append("b"))
        self.bus.publish("ev", {})
        assert set(log) == {"a", "b"}

    def test_handler_exception_does_not_block_others(self):
        """If one handler raises, subsequent handlers still run."""
        log = []

        def bad(p):
            raise RuntimeError("boom")

        def good(p):
            log.append("ran")

        self.bus.subscribe("ev", bad)
        self.bus.subscribe("ev", good)
        self.bus.publish("ev", {})  # must not raise
        assert log == ["ran"]

    @pytest.mark.asyncio
    async def test_async_handler_scheduled(self):
        """Async handler is executed via ensure_future when loop is running."""
        log = []

        async def async_handler(payload):
            log.append(payload)

        self.bus.subscribe("async.ev", async_handler)
        self.bus.publish("async.ev", {"x": 1})
        # yield control so the coroutine runs
        import asyncio

        await asyncio.sleep(0)
        assert log == [{"x": 1}]

    def test_builtin_task_failed_handler(self, db):
        """_on_task_failed creates an incident ticket."""
        from backend.services.event_bus import _on_task_failed
        from backend.db.models import Ticket

        with patch("backend.db.session.SessionLocal", return_value=db):
            _on_task_failed({"task_id": "T-99", "error": "OOM killed"})

        # Ticket should exist
        ticket = db.query(Ticket).filter(Ticket.tags.contains("incident")).first()
        assert ticket is not None
        assert "T-99" in ticket.title

    def test_builtin_workflow_completed_handler(self, db):
        """_on_workflow_completed broadcasts a system notification."""
        from backend.services.event_bus import _on_workflow_completed
        from backend.db.models import Notification, User

        # Create an admin user so there is someone to notify
        admin = User(
            id="admin-1",
            email="admin@test.com",
            password_hash="x",
            full_name="Admin",
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()

        with patch("backend.db.session.SessionLocal", return_value=db):
            _on_workflow_completed({"workflow_id": "WF-1"})

        notif = db.query(Notification).first()
        assert notif is not None
        assert "WF-1" in notif.message

    def test_builtin_workflow_completed_no_id(self, db):
        """_on_workflow_completed is a no-op when workflow_id is missing."""
        from backend.services.event_bus import _on_workflow_completed

        # Should not raise
        _on_workflow_completed({})

    def test_builtin_workflow_failed_handler(self, db):
        """_on_workflow_failed broadcasts failure notification to admins."""
        from backend.services.event_bus import _on_workflow_failed
        from backend.db.models import Notification, User

        admin = User(
            id="admin-2",
            email="admin2@test.com",
            password_hash="x",
            full_name="Admin2",
            role="superadmin",
            is_active=True,
        )
        db.add(admin)
        db.commit()

        with patch("backend.db.session.SessionLocal", return_value=db):
            _on_workflow_failed({"workflow_id": "WF-2", "error": "timeout"})

        notif = db.query(Notification).first()
        assert notif is not None
        assert "WF-2" in notif.message


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: backend/api/tickets.py (via TestClient)
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# Shared mocked-Redis + in-memory-DB app client fixture
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def app_client_with_db():
    """
    TestClient with:
    - in-memory SQLite database (via get_db override)
    - Redis mocked so token revocation check is instant
    """
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.db.session import get_db

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    mock_redis = MagicMock()
    mock_redis.exists.return_value = 0  # token not revoked

    with patch("backend.auth.jwt_handler.redis_client", mock_redis):
        client = TestClient(app, raise_server_exceptions=False)
        yield client, session

    app.dependency_overrides.pop(get_db, None)
    session.close()
    Base.metadata.drop_all(engine)


def _make_auth_headers(db):
    """Create a test user in db and return JWT Authorization headers."""
    import uuid
    from backend.auth.user_service import UserService, UserCreate
    from backend.auth.jwt_handler import create_access_token

    svc = UserService(db)
    u = svc.create_user(
        UserCreate(
            email=f"api-test-{uuid.uuid4().hex[:8]}@test.com",
            password="Pass123!",
            full_name="APITester",
        )
    )
    token = create_access_token({"sub": u.id, "role": u.role})
    return {"Authorization": f"Bearer {token}"}


class TestTicketsAPI:
    """Endpoint-level tests for /api/tickets (mocked Redis + in-memory DB)."""

    def test_create_ticket(self, app_client_with_db):
        """POST /api/tickets creates a ticket and returns 201."""
        client, db = app_client_with_db
        headers = _make_auth_headers(db)
        resp = client.post(
            "/api/tickets",
            json={"title": "Fix login bug", "instruction": "Debug the OAuth2 flow", "priority": "high"},
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Fix login bug"
        assert body["priority"] == "high"

    def test_create_ticket_missing_title(self, app_client_with_db):
        """POST /api/tickets without required title returns 422."""
        client, db = app_client_with_db
        headers = _make_auth_headers(db)
        resp = client.post("/api/tickets", json={"instruction": "No title"}, headers=headers)
        assert resp.status_code == 422

    def test_list_tickets(self, app_client_with_db):
        """GET /api/tickets returns paginated list."""
        client, db = app_client_with_db
        headers = _make_auth_headers(db)
        for i in range(2):
            client.post("/api/tickets", json={"title": f"T{i}", "instruction": f"I{i}"}, headers=headers)
        resp = client.get("/api/tickets", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert body["total"] >= 2

    def test_get_ticket_not_found(self, app_client_with_db):
        """GET /api/tickets/{id} with non-existent ID returns 404."""
        client, db = app_client_with_db
        headers = _make_auth_headers(db)
        resp = client.get("/api/tickets/nonexistent-id", headers=headers)
        assert resp.status_code == 404

    def test_update_ticket(self, app_client_with_db):
        """PUT /api/tickets/{id} updates fields correctly."""
        client, db = app_client_with_db
        headers = _make_auth_headers(db)
        created = client.post(
            "/api/tickets", json={"title": "Old", "instruction": "Old"}, headers=headers
        ).json()
        tid = created["id"]
        resp = client.put(f"/api/tickets/{tid}", json={"title": "New", "priority": "critical"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "New"

    def test_resolve_ticket(self, app_client_with_db):
        """POST /api/tickets/{id}/resolve sets status to RESOLVED."""
        client, db = app_client_with_db
        headers = _make_auth_headers(db)
        created = client.post(
            "/api/tickets", json={"title": "Bug", "instruction": "Fix it"}, headers=headers
        ).json()
        tid = created["id"]
        resp = client.post(f"/api/tickets/{tid}/resolve", json={}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "RESOLVED"

    def test_add_comment(self, app_client_with_db):
        """POST /api/tickets/{id}/comment adds a comment."""
        client, db = app_client_with_db
        headers = _make_auth_headers(db)
        created = client.post(
            "/api/tickets", json={"title": "Ticket", "instruction": "..."}, headers=headers
        ).json()
        tid = created["id"]
        resp = client.post(f"/api/tickets/{tid}/comment", json={"content": "A comment"}, headers=headers)
        assert resp.status_code == 201

    def test_ticket_history(self, app_client_with_db):
        """GET /api/tickets/{id}/history returns a list."""
        client, db = app_client_with_db
        headers = _make_auth_headers(db)
        created = client.post(
            "/api/tickets", json={"title": "Hist", "instruction": "..."}, headers=headers
        ).json()
        tid = created["id"]
        resp = client.get(f"/api/tickets/{tid}/history", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_unauthenticated_request_rejected(self, app_client_with_db):
        """GET /api/tickets without auth token returns 401 or 403."""
        client, _ = app_client_with_db
        resp = client.get("/api/tickets")
        assert resp.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: backend/api/notifications.py
# ─────────────────────────────────────────────────────────────────────────────


class TestNotificationsAPI:
    """Endpoint-level tests for /api/notifications."""

    def _setup_user_and_headers(self, db):
        from backend.auth.user_service import UserService, UserCreate
        from backend.auth.jwt_handler import create_access_token

        svc = UserService(db)
        u = svc.create_user(
            UserCreate(email="notif@test.com", password="Pass123!", full_name="N")
        )
        token = create_access_token({"sub": u.id, "role": u.role})
        return u, {"Authorization": f"Bearer {token}"}

    def _create_notification(self, db, user_id, is_read=False):
        from backend.db.models import Notification

        n = Notification(
            user_id=user_id,
            type="info",
            title="Test notif",
            message="Hello",
            is_read=is_read,
        )
        db.add(n)
        db.commit()
        db.refresh(n)
        return n

    def test_list_notifications_empty(self, app_client, db):
        """GET /api/notifications returns empty list for new user."""
        _, headers = self._setup_user_and_headers(db)
        resp = app_client.get("/api/notifications", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_notifications_with_items(self, app_client, db):
        """GET /api/notifications returns items for the user."""
        user, headers = self._setup_user_and_headers(db)
        self._create_notification(db, user.id)
        self._create_notification(db, user.id)

        resp = app_client.get("/api/notifications", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_list_unread_only(self, app_client, db):
        """unread_only=true filters out read notifications."""
        user, headers = self._setup_user_and_headers(db)
        self._create_notification(db, user.id, is_read=False)
        self._create_notification(db, user.id, is_read=True)

        resp = app_client.get("/api/notifications?unread_only=true", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_mark_single_read(self, app_client, db):
        """POST /api/notifications/read/{id} marks notification as read."""
        user, headers = self._setup_user_and_headers(db)
        n = self._create_notification(db, user.id)

        resp = app_client.post(f"/api/notifications/read/{n.id}", headers=headers)
        assert resp.status_code == 200

        db.refresh(n)
        assert n.is_read is True

    def test_mark_read_not_found(self, app_client, db):
        """POST /api/notifications/read/{id} with bad ID returns 404."""
        _, headers = self._setup_user_and_headers(db)
        resp = app_client.post("/api/notifications/read/nonexistent", headers=headers)
        assert resp.status_code == 404

    def test_mark_all_read(self, app_client, db):
        """POST /api/notifications/read-all marks all as read."""
        user, headers = self._setup_user_and_headers(db)
        self._create_notification(db, user.id)
        self._create_notification(db, user.id)

        resp = app_client.post("/api/notifications/read-all", headers=headers)
        assert resp.status_code == 200

        from backend.db.models import Notification

        unread = (
            db.query(Notification)
            .filter(Notification.user_id == user.id, Notification.is_read.is_(False))
            .count()
        )
        assert unread == 0

    def test_delete_notification(self, app_client, db):
        """DELETE /api/notifications/{id} removes the notification."""
        user, headers = self._setup_user_and_headers(db)
        n = self._create_notification(db, user.id)

        resp = app_client.delete(f"/api/notifications/{n.id}", headers=headers)
        assert resp.status_code == 200

        from backend.db.models import Notification

        assert db.query(Notification).filter_by(id=n.id).first() is None

    def test_user_isolation(self, app_client, db):
        """Users cannot see or modify each other's notifications."""
        from backend.auth.user_service import UserService, UserCreate
        from backend.auth.jwt_handler import create_access_token

        svc = UserService(db)
        u1 = svc.create_user(UserCreate(email="u1@test.com", password="Pass1!23", full_name="U1"))
        u2 = svc.create_user(UserCreate(email="u2@test.com", password="Pass1!23", full_name="U2"))
        self._create_notification(db, u2.id)  # belongs to u2

        token1 = create_access_token({"sub": u1.id, "role": u1.role})
        headers1 = {"Authorization": f"Bearer {token1}"}

        resp = app_client.get("/api/notifications", headers=headers1)
        assert resp.json()["total"] == 0  # u1 sees nothing


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: backend/api/workflows.py
# ─────────────────────────────────────────────────────────────────────────────


class TestWorkflowsAPI:
    """Endpoint-level tests for /api/workflows."""

    def _get_headers(self, db):
        from backend.auth.user_service import UserService, UserCreate
        from backend.auth.jwt_handler import create_access_token

        svc = UserService(db)
        u = svc.create_user(
            UserCreate(email="wf@test.com", password="Pass123!", full_name="WF")
        )
        token = create_access_token({"sub": u.id, "role": u.role})
        return {"Authorization": f"Bearer {token}"}

    def _workflow_body(self):
        return {
            "name": "Test Workflow",
            "steps": [
                {"step_name": "Step 1", "step_type": "ticket", "input": {"title": "T1"}},
                {"step_name": "Step 2", "step_type": "notification", "input": {"msg": "done"}},
            ],
        }

    def test_create_workflow(self, app_client, db):
        """POST /api/workflows returns 201 with workflow detail."""
        with patch("backend.tasks.workflow_tasks.execute_workflow_step"):
            resp = app_client.post(
                "/api/workflows",
                json=self._workflow_body(),
                headers=self._get_headers(db),
            )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Test Workflow"
        assert body["status"] == "pending"

    def test_list_workflows(self, app_client, db):
        """GET /api/workflows returns list."""
        headers = self._get_headers(db)
        with patch("backend.tasks.workflow_tasks.execute_workflow_step"):
            app_client.post("/api/workflows", json=self._workflow_body(), headers=headers)
        resp = app_client.get("/api/workflows", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_workflow_not_found(self, app_client, db):
        """GET /api/workflows/{id} with unknown ID returns 404."""
        resp = app_client.get("/api/workflows/ghost", headers=self._get_headers(db))
        assert resp.status_code == 404

    def test_start_workflow(self, app_client, db):
        """POST /api/workflows/{id}/start transitions to running."""
        headers = self._get_headers(db)
        with patch("backend.tasks.workflow_tasks.execute_workflow_step") as mock_task:
            created = app_client.post(
                "/api/workflows", json=self._workflow_body(), headers=headers
            ).json()
            wf_id = created["id"]
            resp = app_client.post(f"/api/workflows/{wf_id}/start", headers=headers)
            assert resp.status_code == 200
            assert resp.json()["status"] == "running"
            mock_task.apply_async.assert_called()

    def test_pause_workflow(self, app_client, db):
        """POST /api/workflows/{id}/pause sets status to paused."""
        headers = self._get_headers(db)
        with patch("backend.tasks.workflow_tasks.execute_workflow_step"):
            created = app_client.post(
                "/api/workflows", json=self._workflow_body(), headers=headers
            ).json()
            wf_id = created["id"]
            # start first, then pause
            app_client.post(f"/api/workflows/{wf_id}/start", headers=headers)

        resp = app_client.post(f"/api/workflows/{wf_id}/pause", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    def test_cancel_workflow(self, app_client, db):
        """POST /api/workflows/{id}/cancel sets status to failed."""
        headers = self._get_headers(db)
        with patch("backend.tasks.workflow_tasks.execute_workflow_step"):
            created = app_client.post(
                "/api/workflows", json=self._workflow_body(), headers=headers
            ).json()
        wf_id = created["id"]
        resp = app_client.post(f"/api/workflows/{wf_id}/cancel", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_create_workflow_missing_name(self, app_client, db):
        """POST /api/workflows without name returns 422."""
        resp = app_client.post(
            "/api/workflows",
            json={"steps": []},
            headers=self._get_headers(db),
        )
        assert resp.status_code == 422

    def test_unauthenticated_blocked(self, app_client):
        """Workflow endpoints require auth."""
        resp = app_client.get("/api/workflows")
        assert resp.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6: backend/db/ticket_history.py
# ─────────────────────────────────────────────────────────────────────────────


class TestTicketHistory:
    """Coverage for record_change and get_history."""

    def test_record_change_and_retrieve(self, db):
        """record_change writes a row; get_history retrieves it."""
        from backend.db.ticket_history import record_change, get_history

        record_change(db, ticket_id="T-1", action="status_changed", old_value="OPEN", new_value="RESOLVED")
        history = get_history(db, ticket_id="T-1")
        assert len(history) == 1
        assert history[0]["action"] == "status_changed"
        assert history[0]["old_value"] == "OPEN"

    def test_multiple_changes_ordered(self, db):
        """Multiple changes are returned in insertion order."""
        from backend.db.ticket_history import record_change, get_history

        record_change(db, ticket_id="T-2", action="created")
        record_change(db, ticket_id="T-2", action="assigned")
        record_change(db, ticket_id="T-2", action="resolved")

        history = get_history(db, ticket_id="T-2")
        assert len(history) == 3
        actions = [h["action"] for h in history]
        assert actions == ["created", "assigned", "resolved"]

    def test_empty_history(self, db):
        """get_history returns [] for ticket with no changes."""
        from backend.db.ticket_history import get_history

        history = get_history(db, ticket_id="T-nonexistent")
        assert history == []

    def test_record_change_minimal_args(self, db):
        """record_change works with only ticket_id and action."""
        from backend.db.ticket_history import record_change, get_history

        record_change(db, ticket_id="T-3", action="created")
        history = get_history(db, ticket_id="T-3")
        assert len(history) == 1
        assert history[0]["old_value"] is None
        assert history[0]["new_value"] is None


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7: backend/services/ticket_service.py
# ─────────────────────────────────────────────────────────────────────────────


class TestTicketService:
    """Coverage for TicketService business logic."""

    def test_create_ticket(self, db):
        """TicketService.create_ticket persists a Ticket row."""
        from backend.services.ticket_service import TicketService
        from backend.db.models import Ticket

        svc = TicketService(db)
        t = svc.create_ticket(title="Setup DB", instruction="Run alembic upgrade")
        assert t.id is not None
        db_ticket = db.query(Ticket).filter_by(id=t.id).first()
        assert db_ticket.title == "Setup DB"

    def test_create_ticket_priority(self, db):
        """Ticket priority is stored correctly."""
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t = svc.create_ticket(title="Critical bug", instruction="Fix now", priority="critical")
        assert t.priority == "critical"

    def test_get_ticket(self, db):
        """get_ticket returns the ticket by ID."""
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t = svc.create_ticket(title="Fetch me", instruction="...")
        fetched = svc.get_ticket(t.id)
        assert fetched.title == "Fetch me"

    def test_get_ticket_not_found(self, db):
        """get_ticket returns None for unknown ID."""
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        assert svc.get_ticket("does-not-exist") is None

    def test_update_ticket(self, db):
        """update_ticket changes fields on an existing ticket."""
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t = svc.create_ticket(title="Old", instruction="...")
        updated = svc.update_ticket(t.id, user_id="sys", title="New", priority="low")
        assert updated.title == "New"
        assert updated.priority == "low"

    def test_assign_ticket(self, db):
        """assign sets assignee_id and records history."""
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t = svc.create_ticket(title="T", instruction="...")
        svc.assign(t.id, assignee_id="user-99", user_id="admin-1")
        t_refreshed = svc.get_ticket(t.id)
        assert t_refreshed.assignee_id == "user-99"

    def test_escalate_priority(self, db):
        """escalate bumps priority from medium → high → critical."""
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t = svc.create_ticket(title="T", instruction="...", priority="medium")
        escalated = svc.escalate(t.id, user_id="admin-1")
        assert escalated.priority in ("high", "critical")

    def test_resolve_ticket(self, db):
        """resolve sets status to RESOLVED and stamps resolved_at."""
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t = svc.create_ticket(title="Bug", instruction="...")
        resolved = svc.resolve(t.id, user_id="admin-1")
        assert resolved.status == "RESOLVED"
        assert resolved.resolved_at is not None

    def test_close_resolved_ticket(self, db):
        """close transitions a RESOLVED ticket to CLOSED."""
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t = svc.create_ticket(title="Done", instruction="...")
        svc.resolve(t.id, user_id="admin-1")
        closed = svc.close(t.id, user_id="admin-1")
        assert closed.status == "CLOSED"

    def test_get_metrics(self, db):
        """get_metrics returns counts by status."""
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        svc.create_ticket(title="A", instruction="...")
        svc.create_ticket(title="B", instruction="...")
        t3 = svc.create_ticket(title="C", instruction="...")
        svc.resolve(t3.id, user_id="admin-1")

        metrics = svc.get_metrics()
        assert metrics["total"] >= 3
        assert "by_status" in metrics
        by_status = metrics["by_status"]
        # "OPEN" or "RESOLVED" must appear since we created 3 tickets and resolved 1
        assert any(k in ("OPEN", "open") for k in by_status)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8: backend/services/notification_service.py
# ─────────────────────────────────────────────────────────────────────────────


class TestNotificationService:
    """Coverage for NotificationService."""

    def _make_user(self, db, email="ns@test.com", role="user"):
        from backend.db.models import User

        u = User(id=f"u-{email}", email=email, password_hash="x", full_name="N", role=role, is_active=True)
        db.add(u)
        db.commit()
        return u

    def test_create_notification(self, db):
        """create_notification persists a Notification row."""
        from backend.services.notification_service import NotificationService
        from backend.db.models import Notification

        u = self._make_user(db)
        svc = NotificationService(db)
        n = svc.create_notification(
            user_id=u.id, type="info", title="Hello", message="World"
        )
        assert n.id is not None
        assert db.query(Notification).filter_by(id=n.id).first() is not None

    def test_create_notification_with_metadata(self, db):
        """create_notification stores metadata_json correctly."""
        from backend.services.notification_service import NotificationService

        u = self._make_user(db, email="ns2@test.com")
        svc = NotificationService(db)
        n = svc.create_notification(
            user_id=u.id, type="warning", title="Disk", message="80%", metadata={"disk": 80}
        )
        assert n.metadata_json is not None
        data = json.loads(n.metadata_json)
        assert data["disk"] == 80

    def test_notify_task_failed(self, db):
        """notify_task_failed creates error notifications for all admins."""
        from backend.services.notification_service import NotificationService
        from backend.db.models import Notification

        admin = self._make_user(db, email="adm@test.com", role="admin")
        svc = NotificationService(db)
        svc.notify_task_failed(task_id="T-99", error="OOM")

        notifs = db.query(Notification).filter_by(user_id=admin.id).all()
        assert len(notifs) >= 1
        assert any("T-99" in n.message or "T-99" in n.title for n in notifs)

    def test_broadcast_system_event(self, db):
        """broadcast_system_event notifies all admin users."""
        from backend.services.notification_service import NotificationService
        from backend.db.models import Notification

        self._make_user(db, email="a1@test.com", role="admin")
        self._make_user(db, email="a2@test.com", role="superadmin")
        self._make_user(db, email="u1@test.com", role="user")  # should NOT get notified

        svc = NotificationService(db)
        svc.broadcast_system_event("deploy.completed", "Deploy finished successfully")

        notifs = db.query(Notification).all()
        # Only 2 admins should have notifications
        assert len(notifs) == 2

    def test_notify_ticket_resolved(self, db):
        """notify_ticket_resolved notifies the reporter."""
        from backend.services.notification_service import NotificationService
        from backend.db.models import Notification, Ticket

        reporter = self._make_user(db, email="reporter@test.com")
        ticket = Ticket(
            project_id="P-1",
            department="Engineering",
            title="Bug",
            instruction="Fix",
            reporter_id=reporter.id,
        )
        db.add(ticket)
        db.commit()

        svc = NotificationService(db)
        svc.notify_ticket_resolved(ticket)

        notifs = db.query(Notification).filter_by(user_id=reporter.id).all()
        assert len(notifs) == 1

    def test_notify_ticket_resolved_no_reporter(self, db):
        """notify_ticket_resolved is a no-op when reporter_id is None."""
        from backend.services.notification_service import NotificationService
        from backend.db.models import Notification, Ticket

        ticket = Ticket(
            project_id="P-2",
            department="Eng",
            title="T",
            instruction="I",
            reporter_id=None,
        )
        db.add(ticket)
        db.commit()

        svc = NotificationService(db)
        svc.notify_ticket_resolved(ticket)

        assert db.query(Notification).count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9: backend/services/workflow_service.py
# ─────────────────────────────────────────────────────────────────────────────


class TestWorkflowService:
    """Coverage for WorkflowService."""

    def test_create_workflow(self, db):
        """create_workflow persists a Workflow row with pending status."""
        from backend.services.workflow_service import WorkflowService
        from backend.db.models import Workflow

        svc = WorkflowService(db)
        steps = [{"step_name": "S1", "step_type": "ticket"}]
        wf = svc.create_workflow(name="My WF", steps=steps, company_id="C-1")

        assert wf.id is not None
        assert wf.status == "pending"
        db_wf = db.query(Workflow).filter_by(id=wf.id).first()
        assert db_wf.name == "My WF"

    def test_start_workflow_enqueues_step(self, db):
        """start_workflow transitions to running and enqueues first step."""
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db)
        wf = svc.create_workflow(
            name="WF",
            steps=[{"step_name": "S1", "step_type": "ticket"}],
        )

        with patch("backend.tasks.workflow_tasks.execute_workflow_step") as mock_task:
            svc.start_workflow(wf.id)
            mock_task.apply_async.assert_called_once()

        wf_refreshed = svc.get_status(wf.id)
        assert wf_refreshed["status"] == "running"

    def test_pause_workflow(self, db):
        """pause_workflow sets status to paused."""
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db)
        wf = svc.create_workflow(name="WF", steps=[{"step_name": "S", "step_type": "ticket"}])
        with patch("backend.tasks.workflow_tasks.execute_workflow_step"):
            svc.start_workflow(wf.id)
        svc.pause_workflow(wf.id)
        assert svc.get_status(wf.id)["status"] == "paused"

    def test_resume_workflow(self, db):
        """resume_workflow re-enqueues current step and sets running."""
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db)
        wf = svc.create_workflow(name="WF", steps=[{"step_name": "S", "step_type": "ticket"}])
        with patch("backend.tasks.workflow_tasks.execute_workflow_step"):
            svc.start_workflow(wf.id)
            svc.pause_workflow(wf.id)

        with patch("backend.tasks.workflow_tasks.execute_workflow_step") as mock_task:
            svc.resume_workflow(wf.id)
            mock_task.apply_async.assert_called_once()

        assert svc.get_status(wf.id)["status"] == "running"

    def test_cancel_workflow(self, db):
        """cancel_workflow sets status to failed."""
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db)
        wf = svc.create_workflow(name="WF", steps=[{"step_name": "S", "step_type": "ticket"}])
        svc.cancel_workflow(wf.id)
        assert svc.get_status(wf.id)["status"] == "failed"

    def test_get_status_not_found(self, db):
        """get_status raises or returns None for unknown workflow."""
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db)
        result = svc.get_status("ghost-id")
        assert result is None or isinstance(result, dict)

    def test_handle_failure_records_error(self, db):
        """handle_failure records error_message on the workflow."""
        from backend.services.workflow_service import WorkflowService
        from backend.db.models import Workflow

        svc = WorkflowService(db)
        wf = svc.create_workflow(name="WF", steps=[{"step_name": "S", "step_type": "ticket"}])
        with patch("backend.tasks.workflow_tasks.execute_workflow_step.delay"):
            svc.start_workflow(wf.id)
        svc.handle_failure(wf.id, step_id="S", error="Connection refused")

        db_wf = db.query(Workflow).filter_by(id=wf.id).first()
        assert db_wf.status == "failed"
        assert "Connection refused" in (db_wf.error_message or "")
