"""
Unit tests for the SequencerAgent.

All EmailTools calls, database operations, and EventBus interactions are mocked.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta
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
    from agents.outreach.sequencer_agent import SequencerAgent
    return SequencerAgent(db_session=db)


# ── Sequence creation ─────────────────────────────────────────────────────────

def test_create_sequence_valid(db_session):
    agent = _make_agent(db_session)
    seq = agent.create_sequence({
        "name": "Test Sequence",
        "steps": [
            {"delay_days": 0, "subject_template": "Hi!", "body_template": "Hello there."},
        ],
        "status": "active",
    })
    assert seq.name == "Test Sequence"
    assert seq.status == "active"


def test_create_sequence_max_10_steps(db_session):
    agent = _make_agent(db_session)
    steps = [{"delay_days": i, "subject_template": "s", "body_template": "b"} for i in range(10)]
    seq = agent.create_sequence({"name": "10-step", "steps": steps})
    assert seq is not None


def test_create_sequence_rejects_empty_name(db_session):
    agent = _make_agent(db_session)
    with pytest.raises(ValueError, match="name must be 1"):
        agent.create_sequence({"name": "", "steps": [{"delay_days": 0, "subject_template": "s", "body_template": "b"}]})


def test_create_sequence_rejects_zero_steps(db_session):
    agent = _make_agent(db_session)
    with pytest.raises(ValueError, match="1–10"):
        agent.create_sequence({"name": "Empty", "steps": []})


def test_create_sequence_rejects_11_steps(db_session):
    agent = _make_agent(db_session)
    steps = [{"delay_days": i, "subject_template": "s", "body_template": "b"} for i in range(11)]
    with pytest.raises(ValueError, match="1–10"):
        agent.create_sequence({"name": "Too Many", "steps": steps})


def test_create_sequence_rejects_invalid_delay_days(db_session):
    agent = _make_agent(db_session)
    with pytest.raises(ValueError, match="delay_days"):
        agent.create_sequence({
            "name": "Bad",
            "steps": [{"delay_days": 400, "subject_template": "s", "body_template": "b"}],
        })


def test_create_sequence_rejects_empty_subject_template(db_session):
    agent = _make_agent(db_session)
    with pytest.raises(ValueError, match="subject_template"):
        agent.create_sequence({
            "name": "Bad",
            "steps": [{"delay_days": 0, "subject_template": "   ", "body_template": "b"}],
        })


def test_create_sequence_rejects_invalid_status(db_session):
    agent = _make_agent(db_session)
    with pytest.raises(ValueError, match="status"):
        agent.create_sequence({
            "name": "Bad status",
            "steps": [{"delay_days": 0, "subject_template": "s", "body_template": "b"}],
            "status": "running",
        })


# ── Enrolment ─────────────────────────────────────────────────────────────────

def test_enroll_creates_enrollment(db_session):
    from backend.db.models import Lead
    from backend.db.models_outreach import SequenceEnrollment

    lead = Lead(id=str(uuid.uuid4()), email="l@example.com", status="NEW")
    db_session.add(lead)
    db_session.commit()

    agent = _make_agent(db_session)
    seq = agent.create_sequence({
        "name": "S", "steps": [{"delay_days": 0, "subject_template": "s", "body_template": "b"}]
    })

    enrollment = agent.enroll_prospect(lead.id, seq.id)
    assert enrollment.lead_id == lead.id
    assert enrollment.current_step == 0


def test_enroll_rejects_duplicate_active(db_session):
    from backend.db.models import Lead

    lead = Lead(id=str(uuid.uuid4()), email="dup@example.com", status="NEW")
    db_session.add(lead)
    db_session.commit()

    agent = _make_agent(db_session)
    seq = agent.create_sequence({
        "name": "S", "steps": [{"delay_days": 0, "subject_template": "s", "body_template": "b"}]
    })

    agent.enroll_prospect(lead.id, seq.id)  # first enrolment OK
    with pytest.raises(ValueError, match="active enrollment"):
        agent.enroll_prospect(lead.id, seq.id)  # duplicate → error


# ── Template rendering ────────────────────────────────────────────────────────

def test_render_template_substitutes_fields(db_session):
    agent = _make_agent(db_session)
    result = agent.render_template(
        "Hi {{first_name}} from {{company}}!",
        {"first_name": "Alice", "company": "Acme"},
    )
    assert result == "Hi Alice from Acme!"


def test_render_template_null_field_becomes_empty_string(db_session):
    agent = _make_agent(db_session)
    result = agent.render_template(
        "Hello {{first_name}} {{last_name}}",
        {"first_name": "Alice", "last_name": None},
    )
    assert "{{" not in result
    assert result == "Hello Alice "


def test_render_template_unknown_token_becomes_empty(db_session):
    agent = _make_agent(db_session)
    result = agent.render_template(
        "Hello {{unknown_field}}",
        {},
    )
    assert "{{" not in result


def test_render_template_all_supported_fields(db_session):
    agent = _make_agent(db_session)
    result = agent.render_template(
        "{{first_name}} {{last_name}} at {{company}} ({{website}})",
        {"first_name": "A", "last_name": "B", "company": "C", "website": "D"},
    )
    assert result == "A B at C (D)"


# ── Step processing ───────────────────────────────────────────────────────────

def test_process_due_steps_sends_email(db_session):
    from backend.db.models import Lead
    from backend.db.models_outreach import SequenceEnrollment, SequenceStepLog

    lead = Lead(
        id=str(uuid.uuid4()),
        email="test@example.com",
        name="Test User",
        company="TestCo",
        status="NEW",
    )
    db_session.add(lead)
    db_session.commit()

    agent = _make_agent(db_session)
    seq = agent.create_sequence({
        "name": "Due Sequence",
        "steps": [{"delay_days": 0, "subject_template": "Hello", "body_template": "Body"}],
    })

    enrollment = SequenceEnrollment(
        id=str(uuid.uuid4()),
        lead_id=lead.id,
        sequence_id=seq.id,
        status="active",
        current_step=0,
        enrolled_at=datetime.utcnow() - timedelta(hours=1),
    )
    db_session.add(enrollment)
    db_session.commit()

    with patch("agents.outreach.email_engine.EmailTools.send_email", return_value="SUCCESS"):
        count = agent.process_due_steps()

    assert count == 1
    log = db_session.query(SequenceStepLog).first()
    assert log.outcome == "sent"


def test_process_due_steps_pauses_on_email_failure(db_session):
    from backend.db.models import Lead
    from backend.db.models_outreach import SequenceEnrollment

    lead = Lead(
        id=str(uuid.uuid4()),
        email="fail@example.com",
        name="Fail User",
        company="FailCo",
        status="NEW",
    )
    db_session.add(lead)
    db_session.commit()

    agent = _make_agent(db_session)
    seq = agent.create_sequence({
        "name": "Fail Sequence",
        "steps": [{"delay_days": 0, "subject_template": "Hello", "body_template": "Body"}],
    })

    enrollment = SequenceEnrollment(
        id=str(uuid.uuid4()),
        lead_id=lead.id,
        sequence_id=seq.id,
        status="active",
        current_step=0,
        enrolled_at=datetime.utcnow() - timedelta(hours=1),
    )
    db_session.add(enrollment)
    db_session.commit()

    with patch("agents.outreach.email_engine.EmailTools.send_email", return_value="ERROR: smtp"):
        agent.process_due_steps()

    db_session.refresh(enrollment)
    assert enrollment.status == "paused"


# ── Reply-halt ────────────────────────────────────────────────────────────────

def test_on_reply_received_halts_enrollment(db_session):
    from backend.db.models import Lead
    from backend.db.models_outreach import SequenceEnrollment

    lead = Lead(id=str(uuid.uuid4()), email="r@example.com", status="CONTACTED")
    db_session.add(lead)
    db_session.commit()

    agent = _make_agent(db_session)
    seq = agent.create_sequence({
        "name": "S", "steps": [{"delay_days": 5, "subject_template": "s", "body_template": "b"}]
    })

    enrollment = agent.enroll_prospect(lead.id, seq.id)
    agent.on_reply_received({"lead_id": lead.id})

    db_session.refresh(enrollment)
    assert enrollment.status == "replied"


def test_on_reply_received_noop_for_missing_lead_id(db_session):
    agent = _make_agent(db_session)
    # Should not raise
    agent.on_reply_received({})
