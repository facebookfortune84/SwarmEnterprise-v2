"""
tests_sovereign/test_api.py
===========================
Phase 1 — TestNotificationsAPI
Phase 2 — TestWorkflowsAPI

Design rules
------------
* `app_client` fixture patches `redis.Redis` **before** `TestClient(app)` is
  created so the module-level Redis connection in jwt_handler.py never
  attempts a real TCP dial.
* `get_db` **and** `get_current_active_user` are both overridden in
  `app.dependency_overrides` — the latter because it calls `SessionLocal()`
  directly inside its body, bypassing the `get_db` dependency.
* JWT tokens are built with the secret / algorithm read from
  `backend.auth.jwt_handler` at runtime — no hardcoded values.
* Every Celery `apply_async` call is patched at its exact import path so no
  broker connection is attempted.
* All assertions match the actual handler return schemas verified from source.
"""

import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.base import Base
from backend.db.models import Notification, User
from backend.db.session import get_db

# ── JWT config read from actual source (no hardcoding) ──────────────────────
from backend.auth.jwt_handler import SECRET_KEY, ALGORITHM
from backend.auth.middleware import get_current_active_user


# ─────────────────────────────────────────────────────────────────────────────
# Shared test DB infrastructure
# ─────────────────────────────────────────────────────────────────────────────

# StaticPool ensures all connections (including those from handler sessions)
# share the exact same in-memory SQLite database rather than creating isolated
# per-connection databases.
TEST_DB_URL = "sqlite://"


def _make_engine_and_factory():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, factory


def _make_token(user_id: str, email: str, role: str = "user") -> str:
    """Build a valid JWT access token using the app's own secret + algo."""
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@contextmanager
def _patched_redis():
    """
    Patch redis.Redis at the point it is consumed by jwt_handler so the
    module-level `redis_client = redis.Redis(...)` call never dials localhost.
    The mock's `.exists()` returns 0 (token not revoked).
    """
    mock_redis_instance = MagicMock()
    mock_redis_instance.exists.return_value = 0
    mock_redis_instance.setex.return_value = True

    with patch("backend.auth.jwt_handler.redis_client", mock_redis_instance):
        yield mock_redis_instance


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Notifications API
# ─────────────────────────────────────────────────────────────────────────────


class TestNotificationsAPI:
    """
    Covers GET /api/notifications, POST /api/notifications/read/{id},
    POST /api/notifications/read-all, DELETE /api/notifications/{id}.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """
        1. Patch redis.Redis before TestClient is created.
        2. Override get_db and get_current_active_user.
        3. Create a test user + two notifications.
        4. Yield the client.
        5. Drop all tables after each test.
        """
        self.engine, self.factory = _make_engine_and_factory()

        # Seed: user + 2 notifications
        db = self.factory()
        self.user_id = str(uuid.uuid4())
        self.user = User(
            id=self.user_id,
            email="notif_user@example.com",
            password_hash="hashed",
            full_name="Notif User",
            role="user",
            is_active=True,
        )
        db.add(self.user)
        db.commit()

        self.notif1_id = str(uuid.uuid4())
        self.notif2_id = str(uuid.uuid4())
        n1 = Notification(
            id=self.notif1_id,
            user_id=self.user_id,
            type="info",
            title="Hello",
            message="First notification",
            is_read=False,
            created_at=datetime.utcnow(),
        )
        n2 = Notification(
            id=self.notif2_id,
            user_id=self.user_id,
            type="warning",
            title="Warning",
            message="Second notification",
            is_read=False,
            created_at=datetime.utcnow(),
        )
        db.add(n1)
        db.add(n2)
        db.commit()
        db.close()

        self.token = _make_token(self.user_id, "notif_user@example.com", "user")
        self.headers = {"Authorization": f"Bearer {self.token}"}

        # Current user dict that the override will return
        self.current_user_dict = {"id": self.user_id, "email": "notif_user@example.com", "role": "user"}

        def override_get_db():
            db = self.factory()
            try:
                yield db
            finally:
                db.close()

        async def override_get_current_active_user():
            return self.current_user_dict

        with _patched_redis():
            from backend.main import app

            app.dependency_overrides[get_db] = override_get_db
            app.dependency_overrides[get_current_active_user] = override_get_current_active_user

            self.client = TestClient(app, raise_server_exceptions=True)
            yield

            app.dependency_overrides.clear()

        Base.metadata.drop_all(bind=self.engine)

    # ── list ──────────────────────────────────────────────────────────────────

    def test_list_notifications_returns_200(self):
        resp = self.client.get("/api/notifications", headers=self.headers)
        assert resp.status_code == 200

    def test_list_notifications_schema(self):
        resp = self.client.get("/api/notifications", headers=self.headers)
        body = resp.json()
        # actual schema: {total, skip, limit, items}
        assert "total" in body
        assert "skip" in body
        assert "limit" in body
        assert "items" in body
        assert body["total"] == 2
        assert body["skip"] == 0
        assert body["limit"] == 50

    def test_list_notifications_items_have_expected_fields(self):
        resp = self.client.get("/api/notifications", headers=self.headers)
        items = resp.json()["items"]
        assert len(items) == 2
        for item in items:
            for field in ("id", "user_id", "type", "title", "message", "is_read", "created_at"):
                assert field in item, f"Missing field: {field}"

    def test_list_notifications_unread_only(self):
        resp = self.client.get("/api/notifications?unread_only=true", headers=self.headers)
        assert resp.status_code == 200
        body = resp.json()
        # both are unread so both should appear
        assert body["total"] == 2

    def test_list_notifications_pagination(self):
        resp = self.client.get("/api/notifications?limit=1&skip=0", headers=self.headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["limit"] == 1
        assert len(body["items"]) == 1

    def test_list_notifications_invalid_token_rejected(self):
        # A token signed with the wrong secret must be rejected at the JWT decode
        # step (get_current_user → decode_token returns None → 401).
        # We build a raw client with NO dependency overrides for this assertion.
        from backend.main import app

        bad_payload = {
            "sub": self.user_id,
            "email": "notif_user@example.com",
            "role": "user",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "iat": datetime.now(timezone.utc),
        }
        bad_token = jwt.encode(bad_payload, "wrong-secret-entirely", algorithm=ALGORITHM)
        # Temporarily clear all overrides so JWT validation is not short-circuited
        saved_overrides = dict(app.dependency_overrides)
        app.dependency_overrides.clear()
        try:
            bare_client = TestClient(app, raise_server_exceptions=False)
            resp = bare_client.get(
                "/api/notifications",
                headers={"Authorization": f"Bearer {bad_token}"},
            )
            assert resp.status_code == 401
        finally:
            app.dependency_overrides.update(saved_overrides)

    # ── mark single read ──────────────────────────────────────────────────────

    def test_mark_read_returns_ok(self):
        resp = self.client.post(
            f"/api/notifications/read/{self.notif1_id}", headers=self.headers
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_mark_read_persists(self):
        self.client.post(
            f"/api/notifications/read/{self.notif1_id}", headers=self.headers
        )
        db = self.factory()
        notif = db.query(Notification).filter(Notification.id == self.notif1_id).first()
        assert notif.is_read is True
        db.close()

    def test_mark_read_not_found(self):
        resp = self.client.post(
            f"/api/notifications/read/{uuid.uuid4()}", headers=self.headers
        )
        assert resp.status_code == 404

    # ── mark all read ─────────────────────────────────────────────────────────

    def test_mark_all_read_returns_ok(self):
        resp = self.client.post("/api/notifications/read-all", headers=self.headers)
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_mark_all_read_persists(self):
        self.client.post("/api/notifications/read-all", headers=self.headers)
        db = self.factory()
        unread = (
            db.query(Notification)
            .filter(Notification.user_id == self.user_id, Notification.is_read.is_(False))
            .count()
        )
        assert unread == 0
        db.close()

    # ── delete ────────────────────────────────────────────────────────────────

    def test_delete_notification_returns_ok(self):
        resp = self.client.delete(
            f"/api/notifications/{self.notif2_id}", headers=self.headers
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_delete_notification_removes_row(self):
        self.client.delete(f"/api/notifications/{self.notif2_id}", headers=self.headers)
        db = self.factory()
        notif = db.query(Notification).filter(Notification.id == self.notif2_id).first()
        assert notif is None
        db.close()

    def test_delete_notification_not_found(self):
        resp = self.client.delete(
            f"/api/notifications/{uuid.uuid4()}", headers=self.headers
        )
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Workflows API
# ─────────────────────────────────────────────────────────────────────────────

_EXECUTE_STEP_PATH = "backend.tasks.workflow_tasks.execute_workflow_step"
_ADVANCE_WF_PATH = "backend.tasks.workflow_tasks.advance_workflow"
_HANDLE_FAILURE_PATH = "backend.tasks.workflow_tasks.handle_step_failure"


class TestWorkflowsAPI:
    """
    Covers POST /api/workflows, GET /api/workflows, GET /api/workflows/{id},
    POST /api/workflows/{id}/start, POST /api/workflows/{id}/pause,
    POST /api/workflows/{id}/resume, POST /api/workflows/{id}/cancel.

    Router prefix verified from backend/api/workflows.py: /api/workflows
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.engine, self.factory = _make_engine_and_factory()

        # Seed: user
        db = self.factory()
        self.user_id = str(uuid.uuid4())
        user = User(
            id=self.user_id,
            email="wf_user@example.com",
            password_hash="hashed",
            full_name="WF User",
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.close()

        self.token = _make_token(self.user_id, "wf_user@example.com", "admin")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.current_user_dict = {"id": self.user_id, "email": "wf_user@example.com", "role": "admin"}

        def override_get_db():
            db = self.factory()
            try:
                yield db
            finally:
                db.close()

        async def override_get_current_active_user():
            return self.current_user_dict

        mock_task = MagicMock()
        mock_task.apply_async.return_value = MagicMock(id="test-task-id")

        with (
            _patched_redis(),
            patch(_EXECUTE_STEP_PATH, mock_task),
            patch(_ADVANCE_WF_PATH, mock_task),
            patch(_HANDLE_FAILURE_PATH, mock_task),
        ):
            from backend.main import app

            app.dependency_overrides[get_db] = override_get_db
            app.dependency_overrides[get_current_active_user] = override_get_current_active_user

            self.client = TestClient(app, raise_server_exceptions=True)
            self.mock_task = mock_task
            yield

            app.dependency_overrides.clear()

        Base.metadata.drop_all(bind=self.engine)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _create_workflow_payload(self, name: str = "Test Workflow") -> dict:
        return {
            "name": name,
            "steps": [
                {"step_name": "step-one", "step_type": "condition", "input": {"condition": True}},
                {"step_name": "step-two", "step_type": "condition", "input": {"condition": True}},
            ],
        }

    def _create_workflow(self, name: str = "Test Workflow") -> dict:
        resp = self.client.post(
            "/api/workflows",
            json=self._create_workflow_payload(name),
            headers=self.headers,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    # ── create ────────────────────────────────────────────────────────────────

    def test_create_workflow_returns_201(self):
        resp = self.client.post(
            "/api/workflows",
            json=self._create_workflow_payload(),
            headers=self.headers,
        )
        assert resp.status_code == 201

    def test_create_workflow_response_schema(self):
        body = self._create_workflow()
        # get_status returns: id, name, status, current_step, total_steps,
        #   error_message, created_at, updated_at, completed_at, steps
        for field in ("id", "name", "status", "current_step", "total_steps", "steps"):
            assert field in body, f"Missing field: {field}"
        assert body["name"] == "Test Workflow"
        assert body["status"] == "pending"
        assert body["total_steps"] == 2

    def test_create_workflow_steps_in_response(self):
        body = self._create_workflow()
        assert len(body["steps"]) == 2
        for step in body["steps"]:
            for field in ("id", "step_name", "step_type", "status"):
                assert field in step

    # ── list ──────────────────────────────────────────────────────────────────

    def test_list_workflows_empty(self):
        resp = self.client.get("/api/workflows", headers=self.headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "skip" in body
        assert "limit" in body

    def test_list_workflows_contains_created(self):
        self._create_workflow("WF-List-Test")
        resp = self.client.get("/api/workflows", headers=self.headers)
        assert resp.status_code == 200
        names = [w["name"] for w in resp.json()["items"]]
        assert "WF-List-Test" in names

    def test_list_workflows_pagination(self):
        self._create_workflow("WF-A")
        self._create_workflow("WF-B")
        resp = self.client.get("/api/workflows?limit=1&skip=0", headers=self.headers)
        assert resp.status_code == 200
        assert resp.json()["limit"] == 1
        assert len(resp.json()["items"]) == 1

    # ── get single ────────────────────────────────────────────────────────────

    def test_get_workflow_returns_200(self):
        wf = self._create_workflow()
        resp = self.client.get(f"/api/workflows/{wf['id']}", headers=self.headers)
        assert resp.status_code == 200

    def test_get_workflow_not_found(self):
        resp = self.client.get(f"/api/workflows/{uuid.uuid4()}", headers=self.headers)
        assert resp.status_code == 404

    def test_get_workflow_schema(self):
        wf = self._create_workflow()
        body = self.client.get(f"/api/workflows/{wf['id']}", headers=self.headers).json()
        assert body["id"] == wf["id"]
        assert body["name"] == "Test Workflow"

    # ── start ─────────────────────────────────────────────────────────────────

    def test_start_workflow_transitions_to_running(self):
        wf = self._create_workflow()
        resp = self.client.post(f"/api/workflows/{wf['id']}/start", headers=self.headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_start_workflow_not_found(self):
        resp = self.client.post(f"/api/workflows/{uuid.uuid4()}/start", headers=self.headers)
        assert resp.status_code == 404

    # ── pause ─────────────────────────────────────────────────────────────────

    def test_pause_workflow(self):
        wf = self._create_workflow()
        self.client.post(f"/api/workflows/{wf['id']}/start", headers=self.headers)
        resp = self.client.post(f"/api/workflows/{wf['id']}/pause", headers=self.headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    def test_pause_not_found(self):
        resp = self.client.post(f"/api/workflows/{uuid.uuid4()}/pause", headers=self.headers)
        assert resp.status_code == 404

    # ── resume ────────────────────────────────────────────────────────────────

    def test_resume_workflow(self):
        wf = self._create_workflow()
        wf_id = wf["id"]
        self.client.post(f"/api/workflows/{wf_id}/start", headers=self.headers)
        self.client.post(f"/api/workflows/{wf_id}/pause", headers=self.headers)
        resp = self.client.post(f"/api/workflows/{wf_id}/resume", headers=self.headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_resume_not_found(self):
        resp = self.client.post(f"/api/workflows/{uuid.uuid4()}/resume", headers=self.headers)
        assert resp.status_code == 404

    # ── cancel ────────────────────────────────────────────────────────────────

    def test_cancel_workflow_transitions_to_failed(self):
        wf = self._create_workflow()
        wf_id = wf["id"]
        self.client.post(f"/api/workflows/{wf_id}/start", headers=self.headers)
        resp = self.client.post(f"/api/workflows/{wf_id}/cancel", headers=self.headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "failed"
        assert self.user_id in (body.get("error_message") or "")

    def test_cancel_not_found(self):
        resp = self.client.post(f"/api/workflows/{uuid.uuid4()}/cancel", headers=self.headers)
        assert resp.status_code == 404

    # ── auth guard ────────────────────────────────────────────────────────────

    def test_create_workflow_invalid_token_rejected(self):
        # A token signed with the wrong key must be rejected with 401.
        # Clear overrides temporarily so the real JWT validation runs.
        from backend.main import app

        bad_payload = {
            "sub": self.user_id,
            "email": "wf_user@example.com",
            "role": "admin",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "iat": datetime.now(timezone.utc),
        }
        bad_token = jwt.encode(bad_payload, "totally-wrong-key", algorithm=ALGORITHM)
        saved_overrides = dict(app.dependency_overrides)
        app.dependency_overrides.clear()
        try:
            bare_client = TestClient(app, raise_server_exceptions=False)
            resp = bare_client.post(
                "/api/workflows",
                json=self._create_workflow_payload(),
                headers={"Authorization": f"Bearer {bad_token}"},
            )
            assert resp.status_code == 401
        finally:
            app.dependency_overrides.update(saved_overrides)
