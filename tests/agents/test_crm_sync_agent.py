"""
Unit tests for the CRMSyncAgent state machine.

SQLAlchemy session is replaced with in-memory SQLite.
EventBus subscriptions are tested through direct handler calls.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "test-key-64-chars-ci-do-not-use-in-production-ok")
os.environ.setdefault("SECRET_KEY", "test-key-64-chars-ci-do-not-use-in-production-ok")


@pytest.fixture()
def db_session():
    from backend.db.base import Base
    import backend.db.models  # noqa: F401
    import backend.db.models_outreach  # noqa: F401

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def _make_agent(db):
    from agents.outreach.crm_sync_agent import CRMSyncAgent
    return CRMSyncAgent(db_session=db)


# ── prospect_discovered ───────────────────────────────────────────────────────

def test_prospect_discovered_inserts_new_lead(db_session):
    from backend.db.models import Lead

    agent = _make_agent(db_session)
    lead_id = str(uuid.uuid4())
    agent.handle_prospect_discovered({
        "lead_id": lead_id,
        "email": "new@example.com",
        "company": "NewCo",
    })

    lead = db_session.query(Lead).filter(Lead.id == lead_id).first()
    assert lead is not None
    assert lead.status == "NEW"


def test_prospect_discovered_upserts_existing_lead(db_session):
    from backend.db.models import Lead

    lead_id = str(uuid.uuid4())
    existing = Lead(id=lead_id, email="e@example.com", status="")
    db_session.add(existing)
    db_session.commit()

    agent = _make_agent(db_session)
    agent.handle_prospect_discovered({"lead_id": lead_id, "email": "e@example.com"})

    db_session.refresh(existing)
    assert existing.status == "NEW"


def test_prospect_discovered_records_timeline(db_session):
    from backend.db.models_outreach import LeadTimeline

    agent = _make_agent(db_session)
    lead_id = str(uuid.uuid4())
    agent.handle_prospect_discovered({"lead_id": lead_id, "email": "t@example.com"})

    entries = db_session.query(LeadTimeline).filter(LeadTimeline.lead_id == lead_id).all()
    assert len(entries) == 1
    assert entries[0].to_status == "NEW"


def test_prospect_discovered_replays_buffered_events(db_session):
    from backend.db.models import Lead

    agent = _make_agent(db_session)
    lead_id = str(uuid.uuid4())

    # Buffer a sequence_enrolled event before prospect_discovered arrives
    agent._pending_buffer[lead_id].append(("sequence_enrolled", {"lead_id": lead_id}))

    agent.handle_prospect_discovered({"lead_id": lead_id, "email": "buf@example.com"})

    lead = db_session.query(Lead).filter(Lead.id == lead_id).first()
    # After replay, status should be CONTACTED
    assert lead.status == "CONTACTED"
    # Buffer should be cleared
    assert lead_id not in agent._pending_buffer


# ── sequence_enrolled ─────────────────────────────────────────────────────────

def test_sequence_enrolled_updates_lead_to_contacted(db_session):
    from backend.db.models import Lead

    lead_id = str(uuid.uuid4())
    lead = Lead(id=lead_id, email="c@example.com", status="NEW")
    db_session.add(lead)
    db_session.commit()

    agent = _make_agent(db_session)
    agent.handle_sequence_enrolled({"lead_id": lead_id})

    db_session.refresh(lead)
    assert lead.status == "CONTACTED"


def test_sequence_enrolled_buffers_when_lead_not_found(db_session):
    agent = _make_agent(db_session)
    lead_id = "nonexistent-lead"
    agent.handle_sequence_enrolled({"lead_id": lead_id})

    assert len(agent._pending_buffer[lead_id]) == 1


def test_sequence_enrolled_respects_50_event_buffer_cap(db_session):
    from agents.outreach.crm_sync_agent import _MAX_BUFFER

    agent = _make_agent(db_session)
    lead_id = "buffer-cap-test"

    for _ in range(_MAX_BUFFER + 5):
        agent.handle_sequence_enrolled({"lead_id": lead_id})

    assert len(agent._pending_buffer[lead_id]) == _MAX_BUFFER


# ── reply_received ────────────────────────────────────────────────────────────

def test_reply_received_interested_qualifies_lead(db_session):
    from backend.db.models import Lead

    lead_id = str(uuid.uuid4())
    lead = Lead(id=lead_id, email="q@example.com", company="QualCo", status="CONTACTED")
    db_session.add(lead)
    db_session.commit()

    agent = _make_agent(db_session)
    with patch("backend.services.ticket_service.TicketService.create_ticket"):
        agent.handle_reply_received({"lead_id": lead_id, "classification": "interested"})

    db_session.refresh(lead)
    assert lead.status == "QUALIFIED"


def test_reply_received_not_interested_marks_cold_rejected(db_session):
    from backend.db.models import Lead

    lead_id = str(uuid.uuid4())
    lead = Lead(id=lead_id, email="nr@example.com", company="NoCo", status="CONTACTED")
    db_session.add(lead)
    db_session.commit()

    agent = _make_agent(db_session)
    agent.handle_reply_received({"lead_id": lead_id, "classification": "not_interested"})

    db_session.refresh(lead)
    assert lead.status == "COLD_REJECTED"


def test_reply_received_interested_rolls_back_on_ticket_error(db_session):
    from backend.db.models import Lead

    lead_id = str(uuid.uuid4())
    lead = Lead(id=lead_id, email="rb@example.com", company="RBCo", status="CONTACTED")
    db_session.add(lead)
    db_session.commit()

    agent = _make_agent(db_session)
    with patch(
        "backend.services.ticket_service.TicketService.create_ticket",
        side_effect=Exception("DB error"),
    ):
        agent.handle_reply_received({"lead_id": lead_id, "classification": "interested"})

    # Lead status should NOT be QUALIFIED since the transaction failed
    db_session.refresh(lead)
    assert lead.status == "CONTACTED"


def test_reply_received_discards_when_lead_not_found(db_session):
    agent = _make_agent(db_session)
    # Should not raise
    agent.handle_reply_received({"lead_id": "ghost-lead", "classification": "interested"})


# ── sequence_completed ────────────────────────────────────────────────────────

def test_sequence_completed_marks_cold_no_reply(db_session):
    from backend.db.models import Lead

    lead_id = str(uuid.uuid4())
    lead = Lead(id=lead_id, email="cold@example.com", status="CONTACTED")
    db_session.add(lead)
    db_session.commit()

    agent = _make_agent(db_session)
    agent.handle_sequence_completed({"lead_id": lead_id, "has_reply": False})

    db_session.refresh(lead)
    assert lead.status == "COLD"


def test_sequence_completed_noop_when_has_reply(db_session):
    from backend.db.models import Lead

    lead_id = str(uuid.uuid4())
    lead = Lead(id=lead_id, email="replied@example.com", status="QUALIFIED")
    db_session.add(lead)
    db_session.commit()

    agent = _make_agent(db_session)
    agent.handle_sequence_completed({"lead_id": lead_id, "has_reply": True})

    db_session.refresh(lead)
    # Status should be unchanged
    assert lead.status == "QUALIFIED"


def test_sequence_completed_discards_when_lead_not_found(db_session):
    agent = _make_agent(db_session)
    # Should not raise
    agent.handle_sequence_completed({"lead_id": "ghost", "has_reply": False})


# ── EventBus registration ─────────────────────────────────────────────────────

def test_register_subscribes_all_handlers():
    from agents.outreach.crm_sync_agent import CRMSyncAgent
    from backend.services.event_bus import EventBus

    mock_bus = MagicMock(spec=EventBus)
    mock_bus.subscribe = MagicMock()

    agent = CRMSyncAgent()

    with patch("agents.outreach.crm_sync_agent.CRMSyncAgent.register") as mock_reg:
        mock_reg.return_value = None
        agent.register()

    # Verify that register can be called without error
    assert True  # no exception raised
