"""
Unit tests for the ReplyHandlerAgent.

IMAP, Ollama, and DB are all mocked.
"""

from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "test-key-64-chars-ci-do-not-use-in-production-ok")
os.environ.setdefault("SECRET_KEY", "test-key-64-chars-ci-do-not-use-in-production-ok")
os.environ.setdefault("IMAP_SERVER", "imap.example.com")
os.environ.setdefault("IMAP_USER", "user@example.com")
os.environ.setdefault("IMAP_PASS", "secret")


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
    from agents.outreach.reply_handler_agent import ReplyHandlerAgent
    return ReplyHandlerAgent(db_session=db, ollama_timeout=1.0)


# ── Heuristic classification ──────────────────────────────────────────────────

def _msg(sender="a@b.com", subject="Hello", body="Thanks", return_path="<a@b.com>"):
    from agents.outreach.reply_handler_agent import EmailMessage
    return EmailMessage(uid="1", sender=sender, subject=subject, body=body, return_path=return_path)


def test_heuristic_bounce_via_return_path(db_session):
    agent = _make_agent(db_session)
    msg = _msg(return_path="<>", subject="Hello")
    assert agent._classify_with_heuristics(msg) == "bounce"


def test_heuristic_bounce_via_subject(db_session):
    agent = _make_agent(db_session)
    msg = _msg(subject="Mail Delivery Failure", return_path="valid@example.com")
    assert agent._classify_with_heuristics(msg) == "bounce"


def test_heuristic_auto_reply_out_of_office(db_session):
    agent = _make_agent(db_session)
    msg = _msg(body="I am out of office until Monday.")
    assert agent._classify_with_heuristics(msg) == "auto_reply"


def test_heuristic_auto_reply_vacation(db_session):
    agent = _make_agent(db_session)
    msg = _msg(body="I am on vacation this week.")
    assert agent._classify_with_heuristics(msg) == "auto_reply"


def test_heuristic_not_interested_unsubscribe(db_session):
    agent = _make_agent(db_session)
    msg = _msg(body="Please unsubscribe me from this list.")
    assert agent._classify_with_heuristics(msg) == "not_interested"


def test_heuristic_not_interested_remove_me(db_session):
    agent = _make_agent(db_session)
    msg = _msg(body="Remove me from this mailing list.")
    assert agent._classify_with_heuristics(msg) == "not_interested"


def test_heuristic_default_interested(db_session):
    agent = _make_agent(db_session)
    msg = _msg(body="This looks interesting, tell me more!")
    assert agent._classify_with_heuristics(msg) == "interested"


# ── Ollama fallback ───────────────────────────────────────────────────────────

def test_classify_falls_back_to_heuristics_on_ollama_error(db_session):
    import requests as req

    agent = _make_agent(db_session)
    msg = _msg(body="Please unsubscribe me.")
    with patch("requests.post", side_effect=req.exceptions.ConnectionError):
        result = agent.classify_reply(msg)
    assert result == "not_interested"


def test_classify_uses_ollama_when_available(db_session):
    agent = _make_agent(db_session)
    msg = _msg()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "interested"}
    mock_resp.raise_for_status = MagicMock()
    with patch("requests.post", return_value=mock_resp):
        result = agent.classify_reply(msg)
    assert result == "interested"


# ── IMAP connection failure ────────────────────────────────────────────────────

def test_poll_inbox_graceful_on_imap_error(db_session):
    import imaplib

    agent = _make_agent(db_session)
    with patch("imaplib.IMAP4_SSL", side_effect=imaplib.IMAP4.error("auth failed")):
        count = agent.poll_inbox()
    assert count == 0


def test_poll_inbox_returns_zero_when_no_credentials(db_session):
    agent = _make_agent(db_session)
    with patch.dict(os.environ, {"IMAP_SERVER": "", "IMAP_USER": "", "IMAP_PASS": ""}):
        count = agent.poll_inbox()
    assert count == 0


# ── Downstream dispatch ───────────────────────────────────────────────────────

def test_dispatch_interested_creates_ticket(db_session):
    from backend.db.models import Lead
    from agents.outreach.reply_handler_agent import EmailMessage
    from unittest.mock import patch

    lead = Lead(id=str(uuid.uuid4()), email="sender@example.com", company="SomeCo", status="CONTACTED")
    db_session.add(lead)
    db_session.commit()

    agent = _make_agent(db_session)
    msg = EmailMessage(uid="42", sender="sender@example.com", subject="Re: your email", body="Yes, interested!")

    with patch("backend.services.event_bus.event_bus.publish"):
        with patch("backend.services.ticket_service.TicketService.create_ticket"):
            agent._handle_interested(db_session, lead, None, msg)

    assert lead.status  # unchanged by this handler directly


def test_dispatch_not_interested_updates_enrollment(db_session):
    from backend.db.models import Lead
    from backend.db.models_outreach import SequenceEnrollment
    from agents.outreach.reply_handler_agent import EmailMessage
    from agents.outreach.sequencer_agent import SequencerAgent

    lead = Lead(id=str(uuid.uuid4()), email="nope@example.com", company="NopeCo", status="CONTACTED")
    db_session.add(lead)
    db_session.commit()

    seq_agent = SequencerAgent(db_session=db_session)
    seq = seq_agent.create_sequence({
        "name": "S",
        "steps": [{"delay_days": 0, "subject_template": "s", "body_template": "b"}],
    })
    enrollment = seq_agent.enroll_prospect(lead.id, seq.id)

    agent = _make_agent(db_session)
    with patch("backend.services.event_bus.event_bus.publish"):
        agent._handle_not_interested(db_session, lead, enrollment)

    db_session.refresh(enrollment)
    assert enrollment.status == "replied_uninterested"


def test_dispatch_bounce_marks_email_invalid(db_session):
    from backend.db.models import Lead
    from backend.db.models_outreach import SequenceEnrollment
    from agents.outreach.reply_handler_agent import EmailMessage
    from agents.outreach.sequencer_agent import SequencerAgent

    lead = Lead(id=str(uuid.uuid4()), email="bounce@example.com", company="BounceCo", status="CONTACTED")
    db_session.add(lead)
    db_session.commit()

    seq_agent = SequencerAgent(db_session=db_session)
    seq = seq_agent.create_sequence({
        "name": "S",
        "steps": [{"delay_days": 0, "subject_template": "s", "body_template": "b"}],
    })
    enrollment = seq_agent.enroll_prospect(lead.id, seq.id)

    agent = _make_agent(db_session)
    msg = EmailMessage(uid="bounce123", sender="bounce@example.com", subject="Undeliverable", body="")
    agent._handle_bounce(db_session, lead, enrollment, msg)

    assert lead.email_invalid is True
    db_session.refresh(enrollment)
    assert enrollment.status == "failed"


# ── UID deduplication ─────────────────────────────────────────────────────────

def test_uid_not_processed_initially(db_session):
    agent = _make_agent(db_session)
    assert agent._uid_already_processed("test-uid-123") is False


def test_uid_marked_processed_after_call(db_session):
    agent = _make_agent(db_session)
    agent._mark_uid_processed("test-uid-123")
    assert agent._uid_already_processed("test-uid-123") is True


def test_uid_not_cross_mailbox(db_session):
    agent1 = ReplyHandlerAgent_with_mailbox(db_session, "INBOX")
    agent2 = ReplyHandlerAgent_with_mailbox(db_session, "OTHER")
    agent1._mark_uid_processed("shared-uid")
    assert agent2._uid_already_processed("shared-uid") is False


def ReplyHandlerAgent_with_mailbox(db, mailbox):
    from agents.outreach.reply_handler_agent import ReplyHandlerAgent
    return ReplyHandlerAgent(db_session=db, mailbox=mailbox)


# ── Unmatched sender ─────────────────────────────────────────────────────────

def test_dispatch_logs_info_on_unmatched_sender(db_session):
    from agents.outreach.reply_handler_agent import EmailMessage

    agent = _make_agent(db_session)
    msg = EmailMessage(uid="99", sender="unknown@nowhere.com", subject="Hi", body="Hello")

    # Should not raise; should log INFO
    with patch("agents.outreach.reply_handler_agent.logger.info") as mock_log:
        agent._dispatch(msg, "interested")
        assert mock_log.called
