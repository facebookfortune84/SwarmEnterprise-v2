"""
tests/test_linear_engine.py
=============================
Comprehensive coverage for backend/db/linear_engine.py

Covers all CRUD operations: tickets, projects, leads, usage events, processed events.
"""

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars00")
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars01")
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from backend.db.base import Base


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def engine(db_session):
    from backend.db.linear_engine import LinearEngine

    return LinearEngine(db=db_session)


# ---------------------------------------------------------------------------
# Tests: get_swarm_db factory
# ---------------------------------------------------------------------------


class TestGetSwarmDb:
    def test_returns_engine(self):
        from backend.db.linear_engine import get_swarm_db

        with patch("backend.db.linear_engine.SessionLocal") as mock_sl:
            db = get_swarm_db()
        assert db is not None


# ---------------------------------------------------------------------------
# Tests: LinearEngine.create_ticket
# ---------------------------------------------------------------------------


class TestCreateTicket:
    def test_create_ticket(self, engine):
        t = engine.create_ticket("proj-001", "engineering", "Fix bug", "Investigate the error")
        assert t.id is not None
        assert t.title == "Fix bug"

    def test_create_multiple_tickets(self, engine):
        t1 = engine.create_ticket("proj-002", "eng", "T1", "Inst1")
        t2 = engine.create_ticket("proj-002", "qa", "T2", "Inst2")
        assert t1.id != t2.id


# ---------------------------------------------------------------------------
# Tests: LinearEngine.create_project
# ---------------------------------------------------------------------------


class TestCreateProject:
    def test_create_project_minimal(self, engine):
        p = engine.create_project("proj-A")
        assert p.id == "proj-A"

    def test_create_project_full(self, engine):
        p = engine.create_project(
            "proj-B",
            stripe_session="cs_test_001",
            customer_email="buyer@example.com",
            product_id="prod_001",
            price_id="price_001",
            metadata='{"key": "val"}',
        )
        assert p.id == "proj-B"
        assert p.customer_email == "buyer@example.com"


# ---------------------------------------------------------------------------
# Tests: LinearEngine.create_lead
# ---------------------------------------------------------------------------


class TestCreateLead:
    def test_create_lead_minimal(self, engine):
        lead_id = engine.create_lead("user@example.com")
        assert lead_id is not None

    def test_create_lead_with_all_fields(self, engine):
        lead_id = engine.create_lead(
            "full@example.com",
            name="John Doe",
            company="Acme",
            metadata={"source": "web"},
        )
        assert lead_id is not None

    def test_create_lead_crm_sync_errors_ignored(self, engine):
        """CRM sync failures don't prevent lead creation."""
        with patch("backend.connectors.hubspot.create_contact", side_effect=Exception("hubspot down")):
            lead_id = engine.create_lead("crm-fail@example.com")
        assert lead_id is not None


# ---------------------------------------------------------------------------
# Tests: LinearEngine.list_leads
# ---------------------------------------------------------------------------


class TestListLeads:
    def test_list_leads(self, engine):
        engine.create_lead("lead1@example.com")
        engine.create_lead("lead2@example.com")
        leads = engine.list_leads(limit=50)
        assert len(leads) >= 2

    def test_list_leads_empty(self, db_engine):
        from backend.db.linear_engine import LinearEngine
        from sqlalchemy.orm import sessionmaker

        Session = sessionmaker(bind=db_engine)
        db = Session()
        eng = LinearEngine(db=db)
        leads = eng.list_leads(limit=0)
        assert leads == []
        db.close()


# ---------------------------------------------------------------------------
# Tests: LinearEngine.get_lead
# ---------------------------------------------------------------------------


class TestGetLead:
    def test_get_existing_lead(self, engine):
        lead_id = engine.create_lead("get-lead@example.com")
        result = engine.get_lead(lead_id)
        assert result is not None
        assert result["email"] == "get-lead@example.com"

    def test_get_nonexistent_lead(self, engine):
        result = engine.get_lead("nonexistent-id")
        assert result is None


# ---------------------------------------------------------------------------
# Tests: LinearEngine.record_usage
# ---------------------------------------------------------------------------


class TestRecordUsage:
    def test_record_usage_with_project(self, engine):
        uid = engine.record_usage("proj-001", "invoice_created", amount="4999")
        assert uid is not None

    def test_record_usage_without_project(self, engine):
        uid = engine.record_usage(None, "invoice_paid", metadata={"inv": "INV-001"})
        assert uid is not None

    def test_record_usage_no_amount(self, engine):
        uid = engine.record_usage("proj-002", "login")
        assert uid is not None


# ---------------------------------------------------------------------------
# Tests: LinearEngine.list_usage
# ---------------------------------------------------------------------------


class TestListUsage:
    def test_list_usage_all(self, engine):
        engine.record_usage("proj-003", "action1")
        engine.record_usage("proj-003", "action2")
        events = engine.list_usage(limit=50)
        assert len(events) >= 2

    def test_list_usage_by_project(self, engine):
        engine.record_usage("proj-filter", "ev1")
        events = engine.list_usage(project_id="proj-filter")
        assert all(e["project_id"] == "proj-filter" for e in events)


# ---------------------------------------------------------------------------
# Tests: LinearEngine idempotency (ProcessedEvent)
# ---------------------------------------------------------------------------


class TestProcessedEvents:
    def test_is_event_processed_false_initially(self, engine):
        assert engine.is_event_processed("evt_new_001") is False

    def test_mark_event_processed(self, engine):
        engine.mark_event_processed("evt_proc_001")
        assert engine.is_event_processed("evt_proc_001") is True

    def test_mark_event_processed_idempotent(self, engine):
        engine.mark_event_processed("evt_idem_001")
        engine.mark_event_processed("evt_idem_001")  # second call should not fail
        assert engine.is_event_processed("evt_idem_001") is True


# ---------------------------------------------------------------------------
# Tests: LinearEngine.list_projects
# ---------------------------------------------------------------------------


class TestListProjects:
    def test_list_projects(self, engine):
        engine.create_project("proj-list-001")
        engine.create_project("proj-list-002")
        projects = engine.list_projects(limit=50)
        ids = [p["id"] for p in projects]
        assert "proj-list-001" in ids
        assert "proj-list-002" in ids


# ---------------------------------------------------------------------------
# Tests: LinearEngine.get_project
# ---------------------------------------------------------------------------


class TestGetProject:
    def test_get_existing_project(self, engine):
        engine.create_project("proj-get-001", customer_email="c@x.com")
        result = engine.get_project("proj-get-001")
        assert result is not None
        assert result["id"] == "proj-get-001"

    def test_get_nonexistent_project(self, engine):
        result = engine.get_project("nonexistent-proj")
        assert result is None


# ---------------------------------------------------------------------------
# Tests: LinearEngine.list_tickets
# ---------------------------------------------------------------------------


class TestListTickets:
    def test_list_all_tickets(self, engine):
        engine.create_ticket("proj-t001", "eng", "Ticket A", "Do A")
        engine.create_ticket("proj-t001", "qa", "Ticket B", "Do B")
        tickets = engine.list_tickets(limit=50)
        assert len(tickets) >= 2

    def test_list_tickets_by_project(self, engine):
        engine.create_ticket("proj-only-001", "eng", "Only Ticket", "Only inst")
        tickets = engine.list_tickets(project_id="proj-only-001")
        assert all(t["project_id"] == "proj-only-001" for t in tickets)

    def test_list_tickets_empty_project(self, engine):
        tickets = engine.list_tickets(project_id="no-such-project")
        assert tickets == []


# ---------------------------------------------------------------------------
# Tests: LinearEngine.close
# ---------------------------------------------------------------------------


class TestClose:
    def test_close_engine(self, db_engine):
        from backend.db.linear_engine import LinearEngine
        from sqlalchemy.orm import sessionmaker

        Session = sessionmaker(bind=db_engine)
        db = Session()
        eng = LinearEngine(db=db)
        eng.close()  # Should not raise
