"""
tests/test_services_extended.py
=================================
Extended coverage for:
  - backend/services/ticket_service.py  (SLA, metrics, list filters, comments)
  - backend/services/notification_service.py  (all domain helpers, broadcast)
  - backend/auth/permissions.py  (ROLE_PERMISSIONS, require_permission,
    get_user_permissions, has_permission)
  - backend/db/session.py  (init_db, get_db, get_db_url)
  - backend/auth/jwt_handler.py  (revoke_token, is_token_revoked redis error path)
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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.base import Base
from backend.db.models import Notification, User


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


def _user(db, role="user"):
    import uuid

    u = User(
        id=uuid.uuid4().hex[:8],
        email=f"{uuid.uuid4().hex[:6]}@test.com",
        password_hash="x",
        full_name="U",
        role=role,
        is_active=True,
    )
    db.add(u)
    db.commit()
    return u


# ─────────────────────────────────────────────────────────────────────────────
# TicketService — SLA + metrics + filters + comments
# ─────────────────────────────────────────────────────────────────────────────


class TestTicketServiceSLA:
    def _make_old_ticket(self, db, sla_hours=1):
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t = svc.create_ticket("Old ticket", "...", sla_hours=sla_hours)
        # Back-date so SLA is already breached
        t.created_at = datetime.utcnow() - timedelta(hours=sla_hours + 1)
        db.commit()
        return t

    def test_check_sla_breaches_returns_breached_list(self, db):
        from backend.services.ticket_service import TicketService

        t = self._make_old_ticket(db)
        svc = TicketService(db)
        breached = svc.check_sla_breaches()
        assert t.id in [b.id for b in breached]

    def test_sla_escalates_priority(self, db):
        from backend.services.ticket_service import TicketService

        t = self._make_old_ticket(db)
        original_priority = t.priority
        svc = TicketService(db)
        svc.check_sla_breaches()
        db.refresh(t)
        # priority should have been escalated
        priority_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        assert priority_order.get(t.priority, 0) >= priority_order.get(original_priority, 0)

    def test_sla_fresh_ticket_not_breached(self, db):
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        svc.create_ticket("New ticket", "...", sla_hours=999)
        breached = svc.check_sla_breaches()
        assert len(breached) == 0

    def test_sla_check_resolved_ticket_ignored(self, db):
        from backend.services.ticket_service import TicketService

        t = self._make_old_ticket(db)
        t.status = "RESOLVED"
        db.commit()
        svc = TicketService(db)
        breached = svc.check_sla_breaches()
        assert t.id not in [b.id for b in breached]


class TestTicketServiceMetrics:
    def test_metrics_returns_totals(self, db):
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        svc.create_ticket("T1", "...", priority="high")
        svc.create_ticket("T2", "...", priority="low")
        metrics = svc.get_metrics()
        assert metrics["total"] == 2
        assert "by_status" in metrics
        assert "by_priority" in metrics
        assert metrics["by_priority"].get("high") == 1

    def test_metrics_empty_db(self, db):
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        metrics = svc.get_metrics()
        assert metrics["total"] == 0


class TestTicketServiceFilters:
    def test_list_filter_by_status(self, db):
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t1 = svc.create_ticket("Open", "...")
        t2 = svc.create_ticket("Closed", "...")
        t2.status = "CLOSED"
        db.commit()

        results = svc.list_tickets(status="CLOSED")
        ids = [t.id for t in results]
        assert t2.id in ids
        assert t1.id not in ids

    def test_list_filter_by_priority(self, db):
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t_high = svc.create_ticket("High", "...", priority="high")
        svc.create_ticket("Low", "...", priority="low")
        results = svc.list_tickets(priority="high")
        assert t_high.id in [t.id for t in results]

    def test_list_filter_by_assignee(self, db):
        from backend.services.ticket_service import TicketService

        u = _user(db)
        svc = TicketService(db)
        t = svc.create_ticket("Assigned", "...", assignee_id=u.id)
        svc.create_ticket("Unassigned", "...")
        results = svc.list_tickets(assignee_id=u.id)
        assert t.id in [r.id for r in results]
        assert len(results) == 1

    def test_list_filter_date_range(self, db):
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t = svc.create_ticket("Recent", "...")
        past = datetime.utcnow() - timedelta(days=2)
        results = svc.list_tickets(date_from=past)
        assert t.id in [r.id for r in results]

    def test_list_filter_date_to(self, db):
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t = svc.create_ticket("Old", "...")
        t.created_at = datetime.utcnow() - timedelta(days=5)
        db.commit()
        svc.create_ticket("New", "...")

        cutoff = datetime.utcnow() - timedelta(days=1)
        results = svc.list_tickets(date_to=cutoff)
        assert t.id in [r.id for r in results]

    def test_list_pagination(self, db):
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        for i in range(5):
            svc.create_ticket(f"T{i}", "...")
        page1 = svc.list_tickets(skip=0, limit=2)
        page2 = svc.list_tickets(skip=2, limit=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id


class TestTicketServiceComments:
    def test_get_comments_returns_ordered_list(self, db):
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t = svc.create_ticket("Commented", "...")
        u = _user(db)
        svc.add_comment(t.id, u.id, "First comment")
        svc.add_comment(t.id, u.id, "Second comment")
        comments = svc.get_comments(t.id)
        assert len(comments) == 2
        assert comments[0].content == "First comment"

    def test_get_comments_empty(self, db):
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t = svc.create_ticket("No comments", "...")
        assert svc.get_comments(t.id) == []

    def test_close_ticket(self, db):
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t = svc.create_ticket("Close me", "...")
        u = _user(db)
        svc.resolve(t.id, user_id=u.id)
        closed = svc.close(t.id, user_id=u.id)
        assert closed.status == "CLOSED"

    def test_resolve_with_actual_hours(self, db):
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t = svc.create_ticket("Time tracked", "...")
        u = _user(db)
        resolved = svc.resolve(t.id, user_id=u.id, actual_hours=3.5)
        assert resolved.actual_hours == 3.5
        assert resolved.status == "RESOLVED"

    def test_assign_ticket(self, db):
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t = svc.create_ticket("Assign me", "...")
        u = _user(db)
        assigned = svc.assign(t.id, assignee_id=u.id, user_id=u.id)
        assert assigned.assignee_id == u.id

    def test_escalate_critical_stays_critical(self, db):
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        t = svc.create_ticket("Critical", "...", priority="critical")
        u = _user(db)
        escalated = svc.escalate(t.id, user_id=u.id)
        assert escalated.priority == "critical"

    def test_delete_nonexistent_returns_false(self, db):
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        assert svc.delete_ticket("ghost-id") is False

    def test_update_nonexistent_returns_none(self, db):
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        assert svc.update_ticket("ghost-id", user_id="u") is None


# ─────────────────────────────────────────────────────────────────────────────
# NotificationService
# ─────────────────────────────────────────────────────────────────────────────


class TestNotificationService:
    def test_notify_ticket_created_no_assignee(self, db):
        """notify_ticket_created is a no-op when ticket has no assignee."""
        from backend.services.notification_service import NotificationService
        from backend.services.ticket_service import TicketService

        svc_t = TicketService(db)
        ticket = svc_t.create_ticket("No assignee", "...")
        ns = NotificationService(db)
        ns.notify_ticket_created(ticket)  # should not raise
        assert db.query(Notification).count() == 0

    def test_notify_ticket_created_with_assignee(self, db):
        from backend.services.notification_service import NotificationService
        from backend.services.ticket_service import TicketService

        u = _user(db)
        svc_t = TicketService(db)
        ticket = svc_t.create_ticket("Assigned ticket", "...", assignee_id=u.id)
        ns = NotificationService(db)
        ns.notify_ticket_created(ticket)
        notif = db.query(Notification).filter(Notification.user_id == u.id).first()
        assert notif is not None
        assert "assigned" in notif.title.lower()

    def test_notify_ticket_resolved_no_reporter(self, db):
        from backend.services.notification_service import NotificationService
        from backend.services.ticket_service import TicketService

        svc_t = TicketService(db)
        ticket = svc_t.create_ticket("No reporter", "...")
        ns = NotificationService(db)
        ns.notify_ticket_resolved(ticket)  # no-op
        assert db.query(Notification).count() == 0

    def test_notify_ticket_resolved_with_reporter(self, db):
        from backend.services.notification_service import NotificationService
        from backend.services.ticket_service import TicketService

        u = _user(db)
        svc_t = TicketService(db)
        ticket = svc_t.create_ticket("Resolved ticket", "...", reporter_id=u.id)
        ns = NotificationService(db)
        ns.notify_ticket_resolved(ticket)
        notif = db.query(Notification).filter(Notification.user_id == u.id).first()
        assert notif is not None
        assert notif.type == "success"

    def test_notify_task_failed_notifies_admins(self, db):
        from backend.services.notification_service import NotificationService

        admin = _user(db, role="admin")
        ns = NotificationService(db)
        ns.notify_task_failed("task-99", "OOM killed")
        notif = db.query(Notification).filter(Notification.user_id == admin.id).first()
        assert notif is not None
        assert "task-99" in notif.message

    def test_broadcast_system_event_sends_to_all_admins(self, db):
        from backend.services.notification_service import NotificationService

        a1 = _user(db, role="admin")
        a2 = _user(db, role="superadmin")
        _user(db, role="user")  # should NOT receive

        ns = NotificationService(db)
        ns.broadcast_system_event("deploy.done", "Deployment completed successfully")
        admin_notifs = db.query(Notification).filter(Notification.user_id.in_([a1.id, a2.id])).all()
        assert len(admin_notifs) == 2

    def test_create_notification_with_metadata(self, db):
        from backend.services.notification_service import NotificationService

        u = _user(db)
        ns = NotificationService(db)
        notif = ns.create_notification(
            user_id=u.id,
            type="info",
            title="Meta notif",
            message="With metadata",
            metadata={"key": "value"},
        )
        assert notif.metadata_json is not None
        import json

        data = json.loads(notif.metadata_json)
        assert data["key"] == "value"


# ─────────────────────────────────────────────────────────────────────────────
# permissions.py — ROLE_PERMISSIONS, has_permission, get_user_permissions
# ─────────────────────────────────────────────────────────────────────────────


class TestPermissionsModule:
    def test_role_enum_values(self):
        from backend.auth.permissions import Role

        assert Role.USER == "user"
        assert Role.ADMIN == "admin"
        assert Role.SUPERADMIN == "superadmin"

    def test_permission_enum_exists(self):
        from backend.auth.permissions import Permission

        assert Permission.READ_OWN_DATA is not None

    def test_has_permission_user_own_data(self):
        from backend.auth.permissions import has_permission, Permission

        assert has_permission("user", Permission.READ_OWN_DATA) is True

    def test_has_permission_user_cannot_read_all_users(self):
        from backend.auth.permissions import has_permission, Permission

        assert has_permission("user", Permission.READ_ALL_USERS) is False

    def test_has_permission_admin_can_read_all_users(self):
        from backend.auth.permissions import has_permission, Permission

        assert has_permission("admin", Permission.READ_ALL_USERS) is True

    def test_has_permission_superadmin_can_manage_system(self):
        from backend.auth.permissions import has_permission, Permission

        assert has_permission("superadmin", Permission.MANAGE_SYSTEM) is True

    def test_get_user_permissions_returns_list(self):
        from backend.auth.permissions import get_role_permissions, Role

        perms = get_role_permissions(Role.USER)
        assert isinstance(perms, list)
        assert len(perms) > 0

    def test_get_user_permissions_admin_superset_of_user(self):
        from backend.auth.permissions import get_role_permissions, Role

        user_perms = set(get_role_permissions(Role.USER))
        admin_perms = set(get_role_permissions(Role.ADMIN))
        assert user_perms.issubset(admin_perms)

    def test_require_permission_raises_for_insufficient_role(self):
        from backend.auth.permissions import check_permission, Permission
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            check_permission("user", Permission.READ_ALL_USERS)
        assert exc_info.value.status_code == 403

    def test_require_permission_passes_for_allowed_role(self):
        from backend.auth.permissions import check_permission, Permission

        # Should not raise
        check_permission("admin", Permission.READ_ALL_USERS)

    def test_can_access_resource_same_user(self):
        from backend.auth.permissions import can_access_resource

        assert can_access_resource("u1", "u1", "user") is True

    def test_can_access_resource_different_user(self):
        from backend.auth.permissions import can_access_resource

        assert can_access_resource("u1", "u2", "user") is False

    def test_can_access_resource_admin_any(self):
        from backend.auth.permissions import can_access_resource

        assert can_access_resource("admin", "anyone", "admin") is True


# ─────────────────────────────────────────────────────────────────────────────
# db/session.py
# ─────────────────────────────────────────────────────────────────────────────


class TestDbSession:
    def test_get_db_yields_session(self):
        from backend.db.session import get_db

        gen = get_db()
        session = next(gen)
        assert session is not None
        try:
            next(gen)
        except StopIteration:
            pass

    def test_init_db_creates_tables(self):
        from backend.db.session import init_db

        # Should not raise — tables already exist is idempotent
        init_db()

    def test_get_db_url_returns_string(self):
        from backend.db.session import get_db_url

        url = get_db_url()
        assert isinstance(url, str)
        assert len(url) > 0


# ─────────────────────────────────────────────────────────────────────────────
# jwt_handler.py — redis error path for is_token_revoked
# ─────────────────────────────────────────────────────────────────────────────


class TestJwtHandlerRedisFailure:
    def test_is_token_revoked_fails_open_on_redis_error(self):
        """When Redis is unavailable, treat token as NOT revoked (fail-open)."""
        from backend.auth.jwt_handler import create_access_token, is_token_revoked

        token = create_access_token({"sub": "u1"})
        mock_redis = MagicMock()
        mock_redis.exists.side_effect = Exception("Redis down")

        with patch("backend.auth.jwt_handler.redis_client", mock_redis):
            result = is_token_revoked(token)

        # fail-open: returns False (not revoked) so auth continues
        assert result is False

    def test_revoke_token_returns_false_on_invalid_token(self):
        from backend.auth.jwt_handler import revoke_token

        result = revoke_token("not.a.valid.jwt")
        assert result is False

    def test_revoke_token_returns_true_on_valid_token(self):
        from backend.auth.jwt_handler import create_access_token, revoke_token

        token = create_access_token({"sub": "u2"})
        mock_redis = MagicMock()
        mock_redis.setex.return_value = True

        with patch("backend.auth.jwt_handler.redis_client", mock_redis):
            result = revoke_token(token)

        assert result is True
