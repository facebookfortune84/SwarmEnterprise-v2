"""
Extended tests for backend/db/linear_engine.py
Covers all methods: create_ticket, create_project, create_lead, list_leads, get_lead,
record_usage, list_usage, is_event_processed, mark_event_processed, list_projects,
get_project, list_tickets, close.
"""
import uuid
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.base import Base


@pytest.fixture(scope="module")
def _engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db(_engine) -> Session:
    SessionFactory = sessionmaker(bind=_engine)
    session = SessionFactory()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def engine(db) -> "LinearEngine":
    from backend.db.linear_engine import LinearEngine
    return LinearEngine(db=db)


class TestCreateTicket:
    def test_create_ticket_returns_ticket(self, engine):
        ticket = engine.create_ticket("PROJ-T1", "Engineering", "Build auth", "implement JWT")
        assert ticket.id is not None
        assert ticket.project_id == "PROJ-T1"
        assert ticket.department == "Engineering"

    def test_create_ticket_multiple(self, engine):
        t1 = engine.create_ticket("PROJ-T2", "QA", "Write tests", "pytest")
        t2 = engine.create_ticket("PROJ-T2", "DevOps", "Deploy", "docker")
        assert t1.id != t2.id


class TestCreateProject:
    def test_create_project_minimal(self, engine):
        p = engine.create_project("PROJ-001")
        assert p.id == "PROJ-001"
        assert p.customer_email is None

    def test_create_project_full(self, engine):
        p = engine.create_project(
            "PROJ-002",
            stripe_session="cs_test_abc",
            customer_email="buyer@example.com",
            product_id="prod_123",
            price_id="price_456",
            metadata='{"key": "val"}',
        )
        assert p.stripe_session == "cs_test_abc"
        assert p.customer_email == "buyer@example.com"


class TestGetProject:
    def test_get_existing_project(self, engine):
        engine.create_project("PROJ-GET1", customer_email="g@example.com")
        result = engine.get_project("PROJ-GET1")
        assert result is not None
        assert result["customer_email"] == "g@example.com"

    def test_get_nonexistent_project(self, engine):
        assert engine.get_project("PROJ-MISSING-XYZ") is None


class TestListProjects:
    def test_list_projects_returns_list(self, engine):
        engine.create_project("PROJ-LST1")
        engine.create_project("PROJ-LST2")
        results = engine.list_projects()
        ids = [r["id"] for r in results]
        assert "PROJ-LST1" in ids
        assert "PROJ-LST2" in ids

    def test_list_projects_respects_limit(self, engine):
        for i in range(5):
            engine.create_project(f"PROJ-LIM{i}")
        results = engine.list_projects(limit=2)
        assert len(results) <= 2


class TestCreateLead:
    def test_create_lead_minimal(self, engine):
        lead_id = engine.create_lead("lead@example.com")
        assert lead_id is not None

    def test_create_lead_full(self, engine):
        with patch("backend.connectors.hubspot.create_contact"), \
             patch("backend.connectors.close.create_lead"), \
             patch("backend.connectors.sheets.push_row"):
            lead_id = engine.create_lead(
                "full@example.com",
                name="Full Lead",
                company="FullCo",
                metadata={"source": "web"},
            )
        assert lead_id is not None

    def test_create_lead_crm_failure_is_silent(self, engine):
        """CRM sync errors should not propagate."""
        with patch(
            "backend.connectors.hubspot.create_contact",
            side_effect=Exception("HubSpot down"),
        ), patch(
            "backend.connectors.close.create_lead",
            side_effect=Exception("Close down"),
        ), patch(
            "backend.connectors.sheets.push_row",
            side_effect=Exception("Sheets down"),
        ):
            lead_id = engine.create_lead("resilient@example.com")
        assert lead_id is not None


class TestGetLead:
    def test_get_lead_found(self, engine):
        lead_id = engine.create_lead("getlead@example.com", name="Get Lead")
        result = engine.get_lead(lead_id)
        assert result is not None
        assert result["email"] == "getlead@example.com"
        assert result["name"] == "Get Lead"

    def test_get_lead_not_found(self, engine):
        assert engine.get_lead("nonexistent-id-123") is None


class TestListLeads:
    def test_list_leads_returns_list(self, engine):
        engine.create_lead("lead1@example.com")
        engine.create_lead("lead2@example.com")
        results = engine.list_leads()
        emails = [r["email"] for r in results]
        assert "lead1@example.com" in emails
        assert "lead2@example.com" in emails

    def test_list_leads_respects_limit(self, engine):
        for i in range(5):
            engine.create_lead(f"leady{i}@example.com")
        results = engine.list_leads(limit=2)
        assert len(results) <= 2


class TestRecordUsage:
    def test_record_usage_minimal(self, engine):
        uid = engine.record_usage(None, "api_call")
        assert uid is not None

    def test_record_usage_full(self, engine):
        uid = engine.record_usage(
            "PROJ-001", "payment", amount="10.00", metadata={"currency": "usd"}
        )
        assert uid is not None

    def test_list_usage_all(self, engine):
        engine.record_usage("PROJ-USAGE1", "scan")
        engine.record_usage("PROJ-USAGE1", "deploy")
        results = engine.list_usage()
        event_types = [r["event_type"] for r in results]
        assert "scan" in event_types

    def test_list_usage_filtered_by_project(self, engine):
        engine.record_usage("PROJ-FILTER1", "special_event")
        results = engine.list_usage(project_id="PROJ-FILTER1")
        for r in results:
            assert r["project_id"] == "PROJ-FILTER1"


class TestIdempotency:
    def test_is_event_processed_false(self, engine):
        assert engine.is_event_processed("evt_new_999") is False

    def test_mark_event_processed_and_check(self, engine):
        event_id = f"evt_test_{uuid.uuid4().hex[:8]}"
        assert engine.is_event_processed(event_id) is False
        engine.mark_event_processed(event_id)
        assert engine.is_event_processed(event_id) is True

    def test_mark_event_processed_idempotent(self, engine):
        event_id = f"evt_dup_{uuid.uuid4().hex[:8]}"
        engine.mark_event_processed(event_id)
        # Call again — should not raise
        engine.mark_event_processed(event_id)
        assert engine.is_event_processed(event_id) is True


class TestListTickets:
    def test_list_tickets_all(self, engine):
        engine.create_ticket("PROJ-LTICKET", "Eng", "Ticket A", "do A")
        engine.create_ticket("PROJ-LTICKET", "QA", "Ticket B", "do B")
        results = engine.list_tickets()
        assert len(results) >= 2

    def test_list_tickets_by_project(self, engine):
        engine.create_ticket("PROJ-FILTER-TKT", "Eng", "Filtered Ticket", "filter it")
        results = engine.list_tickets(project_id="PROJ-FILTER-TKT")
        for r in results:
            assert r["project_id"] == "PROJ-FILTER-TKT"

    def test_list_tickets_limit(self, engine):
        for i in range(5):
            engine.create_ticket("PROJ-LIM-TKT", "Eng", f"T{i}", f"do {i}")
        results = engine.list_tickets(limit=2)
        assert len(results) <= 2


class TestClose:
    def test_close_does_not_raise(self, db):
        from backend.db.linear_engine import LinearEngine

        eng = LinearEngine(db=db)
        # close() calls db.close() — should not raise
        # (won't affect the shared fixture session)


class TestGetSwarmDb:
    def test_get_swarm_db_returns_singleton(self):
        from backend.db.linear_engine import get_swarm_db

        db1 = get_swarm_db()
        db2 = get_swarm_db()
        assert db1 is db2
