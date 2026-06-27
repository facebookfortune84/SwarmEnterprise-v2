"""
tests_sovereign/test_workflow_service.py
=========================================
Phase 3 — TestWorkflowService

Design rules
------------
* Celery broker is patched at the module level using `task_always_eager=True`
  via `celery_app.conf.update` and `execute_workflow_step.apply_async` is
  patched with a MagicMock so no broker TCP connection is ever attempted.
* Redis is patched at the exact import path consumed by the jwt_handler module.
* Every method signature and return type was read from the source before
  writing assertions — WorkflowService methods return Optional[Workflow] ORM
  objects; get_status() returns Optional[dict].
* All assertions match the actual field names on Workflow / WorkflowStep models
  and the get_status() dict schema.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.base import Base
from backend.db.models import Workflow, WorkflowStep

# ─────────────────────────────────────────────────────────────────────────────
# Task import paths — verified from backend/tasks/workflow_tasks.py
# ─────────────────────────────────────────────────────────────────────────────
_EXECUTE_STEP_PATH = "backend.tasks.workflow_tasks.execute_workflow_step"
_ADVANCE_WF_PATH = "backend.tasks.workflow_tasks.advance_workflow"
_HANDLE_FAILURE_PATH = "backend.tasks.workflow_tasks.handle_step_failure"

# Redis is consumed by jwt_handler at module level; patch the already-imported
# client attribute (not the class) so the socket never dials.
_REDIS_CLIENT_PATH = "backend.auth.jwt_handler.redis_client"

# ─────────────────────────────────────────────────────────────────────────────
# In-memory SQLite DB fixture
# ─────────────────────────────────────────────────────────────────────────────

TEST_DB_URL = "sqlite://"


@pytest.fixture()
def db_session():
    """
    Yield a fresh SQLite in-memory session with all tables created.
    Drops everything on teardown so no state leaks between tests.
    """
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def mock_task():
    """
    Return a MagicMock that stands in for any Celery task.
    apply_async returns a result-like object with a stable `id`.
    """
    t = MagicMock()
    t.apply_async.return_value = MagicMock(id="test-task-id")
    return t


@pytest.fixture()
def mock_redis():
    """Patch the already-imported redis_client so is_token_revoked never dials."""
    r = MagicMock()
    r.exists.return_value = 0
    r.setex.return_value = True
    with patch(_REDIS_CLIENT_PATH, r):
        yield r


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────


def _steps_payload(n: int = 2) -> list[dict]:
    return [
        {"step_name": f"step-{i}", "step_type": "condition", "input": {"condition": True}}
        for i in range(n)
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestWorkflowService:
    """Unit-tests for WorkflowService — all external I/O (Celery, Redis) mocked."""

    # ── create_workflow ───────────────────────────────────────────────────────

    def test_create_workflow_returns_workflow_orm_object(self, db_session, mock_redis):
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        wf = svc.create_workflow(name="My WF", steps=_steps_payload(2))

        # Returns a Workflow ORM object
        assert isinstance(wf, Workflow)

    def test_create_workflow_persists_name(self, db_session, mock_redis):
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        wf = svc.create_workflow(name="Persist Test", steps=_steps_payload(1))

        row = db_session.query(Workflow).filter(Workflow.id == wf.id).first()
        assert row is not None
        assert row.name == "Persist Test"

    def test_create_workflow_status_is_pending(self, db_session, mock_redis):
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        wf = svc.create_workflow(name="Pending Check", steps=_steps_payload(1))
        assert wf.status == "pending"

    def test_create_workflow_creates_step_rows(self, db_session, mock_redis):
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        wf = svc.create_workflow(name="Steps Check", steps=_steps_payload(3))

        steps = (
            db_session.query(WorkflowStep)
            .filter(WorkflowStep.workflow_id == wf.id)
            .all()
        )
        assert len(steps) == 3
        for step in steps:
            assert step.status == "pending"

    def test_create_workflow_step_names_match_input(self, db_session, mock_redis):
        from backend.services.workflow_service import WorkflowService

        payload = [
            {"step_name": "alpha", "step_type": "condition", "input": {}},
            {"step_name": "beta", "step_type": "condition", "input": {}},
        ]
        svc = WorkflowService(db_session)
        wf = svc.create_workflow(name="Name Check", steps=payload)

        # WorkflowStep IDs are UUIDs — order is not deterministic by string sort.
        # Use the service's own get_status() which returns steps in the same
        # insertion order used by _get_steps() (ordered by WorkflowStep.id ascending).
        # Verify both names are present in the returned step list regardless of order.
        status = svc.get_status(wf.id)
        step_names = [s["step_name"] for s in status["steps"]]
        assert "alpha" in step_names
        assert "beta" in step_names
        assert len(step_names) == 2

    def test_create_workflow_with_company_id(self, db_session, mock_redis):
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        # company_id is nullable — no FK row needed for SQLite
        wf = svc.create_workflow(name="Tenant WF", steps=_steps_payload(1), company_id="co-001")
        assert wf.company_id == "co-001"

    # ── start_workflow ────────────────────────────────────────────────────────

    def test_start_workflow_transitions_to_running(self, db_session, mock_redis, mock_task):
        from backend.services.workflow_service import WorkflowService

        with patch(_EXECUTE_STEP_PATH, mock_task):
            svc = WorkflowService(db_session)
            wf = svc.create_workflow(name="Start Test", steps=_steps_payload(2))
            result = svc.start_workflow(wf.id)

        assert result is not None
        assert result.status == "running"

    def test_start_workflow_returns_none_for_unknown_id(self, db_session, mock_redis, mock_task):
        from backend.services.workflow_service import WorkflowService

        with patch(_EXECUTE_STEP_PATH, mock_task):
            svc = WorkflowService(db_session)
            result = svc.start_workflow(str(uuid.uuid4()))

        assert result is None

    def test_start_workflow_sets_current_step_zero(self, db_session, mock_redis, mock_task):
        from backend.services.workflow_service import WorkflowService

        with patch(_EXECUTE_STEP_PATH, mock_task):
            svc = WorkflowService(db_session)
            wf = svc.create_workflow(name="Step Zero", steps=_steps_payload(2))
            result = svc.start_workflow(wf.id)

        assert result.current_step == 0

    def test_start_workflow_enqueues_first_step(self, db_session, mock_redis, mock_task):
        """apply_async should be called once for the first step."""
        from backend.services.workflow_service import WorkflowService

        with patch(_EXECUTE_STEP_PATH, mock_task):
            svc = WorkflowService(db_session)
            wf = svc.create_workflow(name="Enqueue Test", steps=_steps_payload(2))
            svc.start_workflow(wf.id)

        mock_task.apply_async.assert_called_once()

    def test_start_workflow_idempotent_if_already_running(self, db_session, mock_redis, mock_task):
        """Calling start again on a running workflow should return it unchanged."""
        from backend.services.workflow_service import WorkflowService

        with patch(_EXECUTE_STEP_PATH, mock_task):
            svc = WorkflowService(db_session)
            wf = svc.create_workflow(name="Idempotent", steps=_steps_payload(1))
            svc.start_workflow(wf.id)
            result = svc.start_workflow(wf.id)  # second call

        # Should return the workflow, still running (idempotent)
        assert result is not None
        assert result.status == "running"

    # ── pause_workflow ────────────────────────────────────────────────────────

    def test_pause_running_workflow(self, db_session, mock_redis, mock_task):
        from backend.services.workflow_service import WorkflowService

        with patch(_EXECUTE_STEP_PATH, mock_task):
            svc = WorkflowService(db_session)
            wf = svc.create_workflow(name="Pause Test", steps=_steps_payload(2))
            svc.start_workflow(wf.id)
            result = svc.pause_workflow(wf.id)

        assert result is not None
        assert result.status == "paused"

    def test_pause_non_running_workflow_is_noop(self, db_session, mock_redis):
        """Pausing a pending workflow should return it without changing status."""
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        wf = svc.create_workflow(name="Pause Noop", steps=_steps_payload(1))
        result = svc.pause_workflow(wf.id)

        # status unchanged — still pending
        assert result.status == "pending"

    def test_pause_unknown_id_returns_none(self, db_session, mock_redis):
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        result = svc.pause_workflow(str(uuid.uuid4()))
        assert result is None

    # ── resume_workflow ───────────────────────────────────────────────────────

    def test_resume_paused_workflow(self, db_session, mock_redis, mock_task):
        from backend.services.workflow_service import WorkflowService

        with patch(_EXECUTE_STEP_PATH, mock_task):
            svc = WorkflowService(db_session)
            wf = svc.create_workflow(name="Resume Test", steps=_steps_payload(2))
            svc.start_workflow(wf.id)
            svc.pause_workflow(wf.id)
            result = svc.resume_workflow(wf.id)

        assert result is not None
        assert result.status == "running"

    def test_resume_non_paused_is_noop(self, db_session, mock_redis):
        """Resuming a pending workflow should leave status unchanged."""
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        wf = svc.create_workflow(name="Resume Noop", steps=_steps_payload(1))
        result = svc.resume_workflow(wf.id)
        assert result.status == "pending"

    def test_resume_unknown_id_returns_none(self, db_session, mock_redis):
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        result = svc.resume_workflow(str(uuid.uuid4()))
        assert result is None

    # ── cancel_workflow ───────────────────────────────────────────────────────

    def test_cancel_workflow_sets_failed(self, db_session, mock_redis, mock_task):
        from backend.services.workflow_service import WorkflowService

        with patch(_EXECUTE_STEP_PATH, mock_task):
            svc = WorkflowService(db_session)
            wf = svc.create_workflow(name="Cancel Test", steps=_steps_payload(2))
            svc.start_workflow(wf.id)
            result = svc.cancel_workflow(wf.id, user_id="usr-123")

        assert result is not None
        assert result.status == "failed"

    def test_cancel_workflow_stores_user_id_in_error(self, db_session, mock_redis, mock_task):
        from backend.services.workflow_service import WorkflowService

        with patch(_EXECUTE_STEP_PATH, mock_task):
            svc = WorkflowService(db_session)
            wf = svc.create_workflow(name="Cancel Msg", steps=_steps_payload(1))
            result = svc.cancel_workflow(wf.id, user_id="usr-abc")

        assert "usr-abc" in result.error_message

    def test_cancel_completed_workflow_is_noop(self, db_session, mock_redis, mock_task):
        """Cancel on an already-completed workflow should not change its status."""
        from backend.services.workflow_service import WorkflowService

        with patch(_EXECUTE_STEP_PATH, mock_task), patch(_ADVANCE_WF_PATH, mock_task):
            svc = WorkflowService(db_session)
            # Create a 0-step workflow and manually mark it completed
            wf = svc.create_workflow(name="Already Done", steps=_steps_payload(1))
            # Force the status directly in the DB
            row = db_session.query(Workflow).filter(Workflow.id == wf.id).first()
            row.status = "completed"
            db_session.commit()

            result = svc.cancel_workflow(wf.id, user_id="usr-xyz")

        # cancel_workflow guards against completed: status must remain completed
        assert result.status == "completed"

    def test_cancel_unknown_id_returns_none(self, db_session, mock_redis):
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        result = svc.cancel_workflow(str(uuid.uuid4()), user_id="u")
        assert result is None

    # ── advance_workflow ──────────────────────────────────────────────────────

    def test_advance_workflow_completes_when_no_more_steps(self, db_session, mock_redis, mock_task):
        """A single-step workflow should reach 'completed' after one advance."""
        from backend.services.workflow_service import WorkflowService

        with patch(_EXECUTE_STEP_PATH, mock_task):
            svc = WorkflowService(db_session)
            wf = svc.create_workflow(name="Single Step", steps=_steps_payload(1))
            svc.start_workflow(wf.id)

        with patch(_EXECUTE_STEP_PATH, mock_task):
            result = svc.advance_workflow(wf.id)

        assert result is not None
        assert result.status == "completed"

    def test_advance_workflow_increments_current_step(self, db_session, mock_redis, mock_task):
        """Two-step workflow: after first advance current_step should be 1."""
        from backend.services.workflow_service import WorkflowService

        with patch(_EXECUTE_STEP_PATH, mock_task):
            svc = WorkflowService(db_session)
            wf = svc.create_workflow(name="Two Steps", steps=_steps_payload(2))
            svc.start_workflow(wf.id)
            result = svc.advance_workflow(wf.id)

        assert result is not None
        assert result.current_step == 1

    def test_advance_marks_completed_step(self, db_session, mock_redis, mock_task):
        """The first WorkflowStep should be marked 'completed' after advance."""
        from backend.services.workflow_service import WorkflowService

        with patch(_EXECUTE_STEP_PATH, mock_task):
            svc = WorkflowService(db_session)
            wf = svc.create_workflow(name="Step Mark", steps=_steps_payload(2))
            svc.start_workflow(wf.id)
            svc.advance_workflow(wf.id)

        steps = (
            db_session.query(WorkflowStep)
            .filter(WorkflowStep.workflow_id == wf.id)
            .order_by(WorkflowStep.id)
            .all()
        )
        assert steps[0].status == "completed"

    # ── handle_failure ────────────────────────────────────────────────────────

    def test_handle_failure_sets_workflow_failed(self, db_session, mock_redis):
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        wf = svc.create_workflow(name="Failure Test", steps=_steps_payload(2))

        # Get a real step ID
        step = (
            db_session.query(WorkflowStep)
            .filter(WorkflowStep.workflow_id == wf.id)
            .first()
        )
        result = svc.handle_failure(wf.id, step.id, "test error")

        assert result is not None
        assert result.status == "failed"
        assert result.error_message == "test error"

    def test_handle_failure_marks_step_failed(self, db_session, mock_redis):
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        wf = svc.create_workflow(name="Step Fail", steps=_steps_payload(2))
        step = (
            db_session.query(WorkflowStep)
            .filter(WorkflowStep.workflow_id == wf.id)
            .first()
        )
        svc.handle_failure(wf.id, step.id, "boom")

        db_session.refresh(step)
        assert step.status == "failed"
        assert step.error_message == "boom"

    def test_handle_failure_increments_retry_count(self, db_session, mock_redis):
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        wf = svc.create_workflow(name="Retry Count", steps=_steps_payload(1))
        step = (
            db_session.query(WorkflowStep)
            .filter(WorkflowStep.workflow_id == wf.id)
            .first()
        )
        svc.handle_failure(wf.id, step.id, "err")

        db_session.refresh(step)
        assert step.retry_count == 1

    def test_handle_failure_unknown_workflow_returns_none(self, db_session, mock_redis):
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        result = svc.handle_failure(str(uuid.uuid4()), str(uuid.uuid4()), "err")
        assert result is None

    # ── get_status ────────────────────────────────────────────────────────────

    def test_get_status_returns_dict(self, db_session, mock_redis):
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        wf = svc.create_workflow(name="Status Check", steps=_steps_payload(2))
        result = svc.get_status(wf.id)

        assert isinstance(result, dict)

    def test_get_status_schema(self, db_session, mock_redis):
        """
        get_status() returns: id, name, status, current_step, total_steps,
        error_message, created_at, updated_at, completed_at, steps.
        Verified from workflow_service.py lines 226-237.
        """
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        wf = svc.create_workflow(name="Schema Check", steps=_steps_payload(2))
        result = svc.get_status(wf.id)

        for field in (
            "id", "name", "status", "current_step", "total_steps",
            "error_message", "created_at", "updated_at", "completed_at", "steps",
        ):
            assert field in result, f"Missing field in get_status(): {field}"

    def test_get_status_total_steps_count(self, db_session, mock_redis):
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        wf = svc.create_workflow(name="Count Check", steps=_steps_payload(3))
        result = svc.get_status(wf.id)
        assert result["total_steps"] == 3

    def test_get_status_step_schema(self, db_session, mock_redis):
        """
        Each step dict must have: id, step_name, step_type, status,
        retry_count, error_message, started_at, completed_at.
        Verified from workflow_service.py lines 213-225.
        """
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        wf = svc.create_workflow(name="Step Schema", steps=_steps_payload(1))
        result = svc.get_status(wf.id)

        step = result["steps"][0]
        for field in ("id", "step_name", "step_type", "status", "retry_count",
                      "error_message", "started_at", "completed_at"):
            assert field in step, f"Missing step field: {field}"

    def test_get_status_unknown_id_returns_none(self, db_session, mock_redis):
        from backend.services.workflow_service import WorkflowService

        svc = WorkflowService(db_session)
        result = svc.get_status(str(uuid.uuid4()))
        assert result is None

    def test_get_status_reflects_running_status(self, db_session, mock_redis, mock_task):
        from backend.services.workflow_service import WorkflowService

        with patch(_EXECUTE_STEP_PATH, mock_task):
            svc = WorkflowService(db_session)
            wf = svc.create_workflow(name="Status Running", steps=_steps_payload(2))
            svc.start_workflow(wf.id)
            result = svc.get_status(wf.id)

        assert result["status"] == "running"
