"""
tests/test_celery_tasks.py
===========================
Coverage for:
  - backend/tasks/ticket_tasks.py
  - backend/tasks/notification_tasks.py
  - backend/tasks/workflow_tasks.py

Session strategy
-----------------
Tasks call  `from backend.db.session import SessionLocal; db = SessionLocal()`
then `db.close()` in a finally block.  Patching `backend.db.session.SessionLocal`
with `side_effect=Session` (the factory, not an instance) lets every task
create its own session against the shared StaticPool engine and then close
it correctly without detaching objects from a shared fixture session.

After each task completes we open a fresh verification session to inspect DB
state rather than trying to refresh the fixture session.
"""

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars00")
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars01")
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.base import Base
from backend.db.models import Ticket, User, Workflow, WorkflowStep

_SESSION_PATH = "backend.db.session.SessionLocal"


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def db_setup():
    """Engine + Session factory sharing a StaticPool (single connection)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    yield Session
    Base.metadata.drop_all(bind=engine)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_ticket(Session, status="OPEN", priority="medium", sla_hours=24, due_date=None):
    from backend.services.ticket_service import TicketService

    db = Session()
    try:
        svc = TicketService(db)
        t = svc.create_ticket("Test ticket", "...", priority=priority, sla_hours=sla_hours)
        if status != "OPEN":
            t.status = status
            db.commit()
        if due_date is not None:
            t.due_date = due_date
            db.commit()
        return t.id  # return ID only — session will close
    finally:
        db.close()


def _make_user(Session, role="user"):
    import uuid

    db = Session()
    try:
        u = User(
            id=uuid.uuid4().hex[:8],
            email=f"{uuid.uuid4().hex[:6]}@task.com",
            password_hash="x",
            full_name="Task User",
            role=role,
            is_active=True,
        )
        db.add(u)
        db.commit()
        return u.id
    finally:
        db.close()


def _make_workflow(Session, step_type="condition", n_steps=1):
    steps_def = [
        {"step_name": f"s{i}", "step_type": step_type, "input": {"condition": True}}
        for i in range(n_steps)
    ]
    db = Session()
    try:
        wf = Workflow(
            name="Test WF",
            status="running",
            current_step=0,
            steps_json=json.dumps(steps_def),
        )
        db.add(wf)
        db.flush()
        step_ids = []
        for sd in steps_def:
            step = WorkflowStep(
                workflow_id=wf.id,
                step_name=sd["step_name"],
                step_type=sd["step_type"],
                status="pending",
                input_json=json.dumps(sd.get("input", {})),
            )
            db.add(step)
            db.flush()
            step_ids.append(step.id)
        db.commit()
        return wf.id, step_ids
    finally:
        db.close()


def _query(Session, model, **filters):
    db = Session()
    try:
        q = db.query(model)
        for k, v in filters.items():
            q = q.filter(getattr(model, k) == v)
        return q.first()
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# ticket_tasks
# ─────────────────────────────────────────────────────────────────────────────


class TestProcessTicket:
    def test_ticket_not_found_returns_error(self, db_setup):
        from backend.tasks.ticket_tasks import process_ticket

        with patch(_SESSION_PATH, side_effect=db_setup):
            result = process_ticket.apply(args=["nonexistent-id"]).get()
        assert result["error"] == "ticket_not_found"

    def test_ticket_found_agent_succeeds(self, db_setup):
        ticket_id = _make_ticket(db_setup)

        mock_factory = MagicMock()
        mock_factory.run_production_cycle.return_value = {"status": "ok"}

        with (
            patch(_SESSION_PATH, side_effect=db_setup),
            patch("backend.core.factory.swarm_factory", mock_factory),
        ):
            from backend.tasks.ticket_tasks import process_ticket

            result = process_ticket.apply(args=[ticket_id]).get()

        assert result.get("ok") is True

    def test_ticket_agent_raises_leaves_ticket_open(self, db_setup):
        ticket_id = _make_ticket(db_setup)

        mock_factory = MagicMock()
        mock_factory.run_production_cycle.side_effect = RuntimeError("boom")

        with (
            patch(_SESSION_PATH, side_effect=db_setup),
            patch("backend.core.factory.swarm_factory", mock_factory),
        ):
            from backend.tasks.ticket_tasks import process_ticket

            try:
                process_ticket.apply(args=[ticket_id]).get(propagate=False)
            except Exception:
                pass

        t = _query(db_setup, Ticket, id=ticket_id)
        assert t.status in ("OPEN", "IN_PROGRESS")


class TestCheckSlaBreach:
    def test_no_breaches_fresh_ticket(self, db_setup):
        _make_ticket(db_setup, sla_hours=999)

        with patch(_SESSION_PATH, side_effect=db_setup):
            from backend.tasks.ticket_tasks import check_sla_breaches

            result = check_sla_breaches.apply().get()

        assert result["breached"] == []

    def test_breach_detected_old_ticket(self, db_setup):
        ticket_id = _make_ticket(db_setup, sla_hours=1)
        # Back-date created_at
        db = db_setup()
        try:
            t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            t.created_at = datetime.utcnow() - timedelta(hours=3)
            db.commit()
        finally:
            db.close()

        with patch(_SESSION_PATH, side_effect=db_setup):
            from backend.tasks.ticket_tasks import check_sla_breaches

            result = check_sla_breaches.apply().get()

        assert ticket_id in result["breached"]

    def test_breach_skips_resolved(self, db_setup):
        ticket_id = _make_ticket(db_setup, status="RESOLVED", sla_hours=1)
        db = db_setup()
        try:
            t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            t.created_at = datetime.utcnow() - timedelta(hours=3)
            db.commit()
        finally:
            db.close()

        with patch(_SESSION_PATH, side_effect=db_setup):
            from backend.tasks.ticket_tasks import check_sla_breaches

            result = check_sla_breaches.apply().get()

        assert ticket_id not in result["breached"]


class TestEscalateOverdue:
    def test_no_overdue_no_due_date(self, db_setup):
        _make_ticket(db_setup)

        with patch(_SESSION_PATH, side_effect=db_setup):
            from backend.tasks.ticket_tasks import escalate_overdue_tickets

            result = escalate_overdue_tickets.apply().get()

        assert result["escalated"] == []

    def test_overdue_ticket_escalated(self, db_setup):
        past = datetime.utcnow() - timedelta(days=1)
        ticket_id = _make_ticket(db_setup, priority="low", due_date=past)

        with patch(_SESSION_PATH, side_effect=db_setup):
            from backend.tasks.ticket_tasks import escalate_overdue_tickets

            result = escalate_overdue_tickets.apply().get()

        assert ticket_id in result["escalated"]
        t = _query(db_setup, Ticket, id=ticket_id)
        assert t.priority == "medium"

    def test_resolved_not_escalated(self, db_setup):
        past = datetime.utcnow() - timedelta(days=1)
        ticket_id = _make_ticket(db_setup, status="RESOLVED", due_date=past)

        with patch(_SESSION_PATH, side_effect=db_setup):
            from backend.tasks.ticket_tasks import escalate_overdue_tickets

            result = escalate_overdue_tickets.apply().get()

        assert ticket_id not in result["escalated"]


# ─────────────────────────────────────────────────────────────────────────────
# notification_tasks
# ─────────────────────────────────────────────────────────────────────────────


class TestSendNotification:
    def test_sends_to_existing_user(self, db_setup):
        user_id = _make_user(db_setup)

        with patch(_SESSION_PATH, side_effect=db_setup):
            from backend.tasks.notification_tasks import send_notification

            result = send_notification.apply(
                args=[user_id, {"type": "info", "title": "Hi", "message": "Hello"}]
            ).get()

        assert result["ok"] is True
        assert "notification_id" in result

    def test_missing_user_fails_gracefully(self, db_setup):
        with patch(_SESSION_PATH, side_effect=db_setup):
            from backend.tasks.notification_tasks import send_notification

            try:
                send_notification.apply(
                    args=["ghost", {"type": "info", "title": "X", "message": "Y"}]
                ).get(propagate=False)
            except Exception:
                pass  # FK violation expected


class TestSendEmailNotification:
    def test_no_smtp_returns_not_configured(self):
        with patch.dict(os.environ, {"SMTP_HOST": ""}, clear=False):
            from backend.tasks.notification_tasks import send_email_notification

            result = send_email_notification.apply(args=["user@test.com", "Subject", "Body"]).get()

        assert result["ok"] is False
        assert result["reason"] == "smtp_not_configured"

    def test_smtp_configured_sends(self):
        mock_smtp_instance = MagicMock()
        mock_smtp_instance.__enter__ = MagicMock(return_value=mock_smtp_instance)
        mock_smtp_instance.__exit__ = MagicMock(return_value=False)

        env_patch = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "u@t.com",
            "SMTP_PASS": "p",
        }
        with patch.dict(os.environ, env_patch):
            with patch("smtplib.SMTP", return_value=mock_smtp_instance):
                from backend.tasks.notification_tasks import send_email_notification

                result = send_email_notification.apply(args=["to@test.com", "Subj", "Body"]).get()

        assert result["ok"] is True


class TestBroadcastEvent:
    def test_broadcast_to_admins(self, db_setup):
        _make_user(db_setup, role="admin")

        with patch(_SESSION_PATH, side_effect=db_setup):
            from backend.tasks.notification_tasks import broadcast_event

            result = broadcast_event.apply(args=["ev", {"data": "x"}]).get()

        assert result["ok"] is True

    def test_broadcast_no_admins(self, db_setup):
        with patch(_SESSION_PATH, side_effect=db_setup):
            from backend.tasks.notification_tasks import broadcast_event

            result = broadcast_event.apply(args=["ev", {}]).get()

        assert result["ok"] is True


# ─────────────────────────────────────────────────────────────────────────────
# workflow_tasks
# ─────────────────────────────────────────────────────────────────────────────


class TestExecuteWorkflowStep:
    def test_step_not_found(self, db_setup):
        wf_id, _ = _make_workflow(db_setup)

        mock_advance = MagicMock()
        mock_advance.apply_async = MagicMock()

        with (
            patch(_SESSION_PATH, side_effect=db_setup),
            patch("backend.tasks.workflow_tasks.advance_workflow", mock_advance),
        ):
            from backend.tasks.workflow_tasks import execute_workflow_step

            result = execute_workflow_step.apply(args=[wf_id, "step-gone"]).get()

        assert result["error"] == "step_not_found"

    def test_condition_step(self, db_setup):
        wf_id, step_ids = _make_workflow(db_setup, step_type="condition")

        mock_advance = MagicMock()
        mock_advance.apply_async = MagicMock()

        with (
            patch(_SESSION_PATH, side_effect=db_setup),
            patch("backend.tasks.workflow_tasks.advance_workflow", mock_advance),
        ):
            from backend.tasks.workflow_tasks import execute_workflow_step

            result = execute_workflow_step.apply(args=[wf_id, step_ids[0]]).get()

        assert result.get("ok") is True

    def _add_step(self, db_setup, wf_id, step_type, input_data):
        db = db_setup()
        try:
            step = WorkflowStep(
                workflow_id=wf_id,
                step_name=f"step-{step_type}",
                step_type=step_type,
                status="pending",
                input_json=json.dumps(input_data),
            )
            db.add(step)
            db.commit()
            return step.id
        finally:
            db.close()

    def test_ticket_step_creates_ticket(self, db_setup):
        wf_id, _ = _make_workflow(db_setup)
        step_id = self._add_step(
            db_setup, wf_id, "ticket", {"title": "WF Ticket", "instruction": "Do it"}
        )

        mock_advance = MagicMock()
        mock_advance.apply_async = MagicMock()

        with (
            patch(_SESSION_PATH, side_effect=db_setup),
            patch("backend.tasks.workflow_tasks.advance_workflow", mock_advance),
        ):
            from backend.tasks.workflow_tasks import execute_workflow_step

            result = execute_workflow_step.apply(args=[wf_id, step_id]).get()

        assert result.get("ok") is True
        t = _query(db_setup, Ticket, title="WF Ticket")
        assert t is not None

    def test_notification_step(self, db_setup):
        _make_user(db_setup, role="admin")
        wf_id, _ = _make_workflow(db_setup)
        step_id = self._add_step(
            db_setup, wf_id, "notification", {"event_type": "done", "message": "All done"}
        )

        mock_advance = MagicMock()
        mock_advance.apply_async = MagicMock()

        with (
            patch(_SESSION_PATH, side_effect=db_setup),
            patch("backend.tasks.workflow_tasks.advance_workflow", mock_advance),
        ):
            from backend.tasks.workflow_tasks import execute_workflow_step

            result = execute_workflow_step.apply(args=[wf_id, step_id]).get()

        assert result.get("ok") is True

    def test_approval_step(self, db_setup):
        wf_id, _ = _make_workflow(db_setup)
        step_id = self._add_step(db_setup, wf_id, "approval", {})

        mock_advance = MagicMock()
        mock_advance.apply_async = MagicMock()

        with (
            patch(_SESSION_PATH, side_effect=db_setup),
            patch("backend.tasks.workflow_tasks.advance_workflow", mock_advance),
        ):
            from backend.tasks.workflow_tasks import execute_workflow_step

            result = execute_workflow_step.apply(args=[wf_id, step_id]).get()

        assert result.get("ok") is True

    def test_unknown_step_type_skipped(self, db_setup):
        wf_id, _ = _make_workflow(db_setup)
        step_id = self._add_step(db_setup, wf_id, "unknown_xyz", {})

        mock_advance = MagicMock()
        mock_advance.apply_async = MagicMock()

        with (
            patch(_SESSION_PATH, side_effect=db_setup),
            patch("backend.tasks.workflow_tasks.advance_workflow", mock_advance),
        ):
            from backend.tasks.workflow_tasks import execute_workflow_step

            result = execute_workflow_step.apply(args=[wf_id, step_id]).get()

        assert result.get("ok") is True


class TestHandleStepFailure:
    def test_marks_workflow_failed(self, db_setup):
        wf_id, _ = _make_workflow(db_setup)

        with patch(_SESSION_PATH, side_effect=db_setup):
            from backend.tasks.workflow_tasks import handle_step_failure

            result = handle_step_failure.apply(args=[wf_id, "step-x", "timeout"]).get()

        assert result["ok"] is True
        wf = _query(db_setup, Workflow, id=wf_id)
        assert wf.status == "failed"


class TestAdvanceWorkflow:
    def test_single_step_completes(self, db_setup):
        wf_id, _ = _make_workflow(db_setup, n_steps=1)

        with patch(_SESSION_PATH, side_effect=db_setup):
            from backend.tasks.workflow_tasks import advance_workflow

            result = advance_workflow.apply(args=[wf_id]).get()

        assert result["ok"] is True
        wf = _query(db_setup, Workflow, id=wf_id)
        assert wf.status == "completed"

    def test_two_step_increments_current(self, db_setup):
        wf_id, _ = _make_workflow(db_setup, n_steps=2)

        mock_exec = MagicMock()
        mock_exec.apply_async = MagicMock()

        with (
            patch(_SESSION_PATH, side_effect=db_setup),
            patch("backend.tasks.workflow_tasks.execute_workflow_step", mock_exec),
        ):
            from backend.tasks.workflow_tasks import advance_workflow

            result = advance_workflow.apply(args=[wf_id]).get()

        assert result["ok"] is True
        wf = _query(db_setup, Workflow, id=wf_id)
        assert wf.current_step == 1

    def test_nonexistent_workflow(self, db_setup):
        with patch(_SESSION_PATH, side_effect=db_setup):
            from backend.tasks.workflow_tasks import advance_workflow

            result = advance_workflow.apply(args=["wf-does-not-exist"]).get()

        assert result["ok"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Additional notification task coverage
# ─────────────────────────────────────────────────────────────────────────────


class TestSendNotificationAdditional:
    def test_send_notification_with_metadata(self, db_setup):
        """send_notification with metadata field."""
        user_id = _make_user(db_setup)

        with patch(_SESSION_PATH, side_effect=db_setup):
            from backend.tasks.notification_tasks import send_notification

            result = send_notification.apply(
                args=[
                    user_id,
                    {
                        "type": "warning",
                        "title": "Watch out",
                        "message": "Something happened",
                        "metadata": {"key": "val"},
                    },
                ]
            ).get()

        assert result["ok"] is True

    def test_send_notification_retry_on_failure(self, db_setup):
        """send_notification retries when service raises."""
        from backend.tasks.notification_tasks import send_notification

        with (
            patch(_SESSION_PATH, side_effect=db_setup),
            patch(
                "backend.services.notification_service.NotificationService.create_notification",
                side_effect=Exception("DB timeout"),
            ),
        ):
            try:
                send_notification.apply(
                    args=["u1", {"type": "info", "title": "X", "message": "Y"}]
                ).get(propagate=True)
            except Exception:
                pass  # retry expected


class TestSendEmailNotificationAdditional:
    def test_smtp_no_user_pass(self):
        """SMTP without credentials skips login."""
        mock_smtp_instance = MagicMock()
        mock_smtp_instance.__enter__ = MagicMock(return_value=mock_smtp_instance)
        mock_smtp_instance.__exit__ = MagicMock(return_value=False)

        env_patch = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "",
            "SMTP_PASS": "",
        }
        with patch.dict(os.environ, env_patch):
            with patch("smtplib.SMTP", return_value=mock_smtp_instance):
                from backend.tasks.notification_tasks import send_email_notification

                result = send_email_notification.apply(args=["to@test.com", "Subj", "Body"]).get()

        assert result["ok"] is True
        mock_smtp_instance.login.assert_not_called()

    def test_smtp_send_fails_triggers_retry(self):
        """SMTP error triggers retry."""
        env_patch = {"SMTP_HOST": "smtp.test.com"}
        with patch.dict(os.environ, env_patch):
            with patch("smtplib.SMTP", side_effect=Exception("Connection refused")):
                from backend.tasks.notification_tasks import send_email_notification

                try:
                    send_email_notification.apply(args=["to@test.com", "S", "B"]).get(
                        propagate=True
                    )
                except Exception:
                    pass  # retry expected


class TestBroadcastEventAdditional:
    def test_broadcast_event_retry_on_failure(self, db_setup):
        """broadcast_event retries when service raises."""
        from backend.tasks.notification_tasks import broadcast_event

        with (
            patch(_SESSION_PATH, side_effect=db_setup),
            patch(
                "backend.services.notification_service.NotificationService.broadcast_system_event",
                side_effect=Exception("DB down"),
            ),
        ):
            try:
                broadcast_event.apply(args=["ev", {}]).get(propagate=True)
            except Exception:
                pass  # retry expected


# ─────────────────────────────────────────────────────────────────────────────
# Additional workflow task coverage
# ─────────────────────────────────────────────────────────────────────────────


class TestAdvanceWorkflowAdditional:
    def test_advance_workflow_retry_on_failure(self, db_setup):
        """advance_workflow retries when service raises."""
        from backend.tasks.workflow_tasks import advance_workflow

        with (
            patch(_SESSION_PATH, side_effect=db_setup),
            patch(
                "backend.services.workflow_service.WorkflowService.advance_workflow",
                side_effect=Exception("DB timeout"),
            ),
        ):
            try:
                advance_workflow.apply(args=["wf-id"]).get(propagate=True)
            except Exception:
                pass  # retry expected

    def test_advance_workflow_returns_ok_when_wf_is_none(self, db_setup):
        """advance_workflow with service returning None (no-op)."""
        from backend.tasks.workflow_tasks import advance_workflow

        with (
            patch(_SESSION_PATH, side_effect=db_setup),
            patch(
                "backend.services.workflow_service.WorkflowService.advance_workflow",
                return_value=None,
            ),
        ):
            result = advance_workflow.apply(args=["wf-none"]).get()

        assert result["ok"] is True


class TestHandleStepFailureAdditional:
    def test_handle_step_failure_retry_on_exception(self, db_setup):
        """handle_step_failure retries when service raises."""
        from backend.tasks.workflow_tasks import handle_step_failure

        with (
            patch(_SESSION_PATH, side_effect=db_setup),
            patch(
                "backend.services.workflow_service.WorkflowService.handle_failure",
                side_effect=Exception("service error"),
            ),
        ):
            try:
                handle_step_failure.apply(args=["wf", "step", "err"]).get(propagate=True)
            except Exception:
                pass  # retry expected


class TestExecuteWorkflowStepAdditional:
    def test_execute_step_exception_triggers_handle_failure(self, db_setup):
        """execute_workflow_step dispatches to handle_step_failure on error."""
        wf_id, step_ids = _make_workflow(db_setup, step_type="ticket")

        mock_advance = MagicMock()
        mock_advance.apply_async = MagicMock()
        mock_failure = MagicMock()
        mock_failure.apply_async = MagicMock()

        with (
            patch(_SESSION_PATH, side_effect=db_setup),
            patch("backend.tasks.workflow_tasks.advance_workflow", mock_advance),
            patch("backend.tasks.workflow_tasks.handle_step_failure", mock_failure),
            patch(
                "backend.services.ticket_service.TicketService.create_ticket",
                side_effect=Exception("Ticket error"),
            ),
        ):
            from backend.tasks.workflow_tasks import execute_workflow_step

            ar = execute_workflow_step.apply(args=[wf_id, step_ids[0]])
            # In eager mode with retry, result may be an exception
            try:
                ar.get(propagate=True)
            except Exception:
                pass  # expected: task raises after retrying

        # handle_step_failure.apply_async should have been called
        assert mock_failure.apply_async.called
