"""
Unit tests for the EnrichmentAgent.

All Ollama HTTP calls and requests.get are mocked.
SQLAlchemy session is replaced with an in-memory SQLite session.
"""

from __future__ import annotations

import json
import os
import pytest
from unittest.mock import MagicMock, patch, call
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ── In-memory SQLite setup ───────────────────────────────────────────────────
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_agent(db):
    from agents.outreach.enrichment_agent import EnrichmentAgent
    return EnrichmentAgent(db_session=db)


# ── Input validation ──────────────────────────────────────────────────────────

def test_run_raises_on_empty_string(db_session):
    agent = _make_agent(db_session)
    with pytest.raises(ValueError, match="at least 1"):
        agent.run("   ")


def test_run_raises_on_too_long_string(db_session):
    agent = _make_agent(db_session)
    niche = "a" * 501
    with pytest.raises(ValueError, match="at most 500"):
        agent.run(niche)


def test_run_accepts_one_char(db_session):
    agent = _make_agent(db_session)
    with patch.object(agent, "_web_search", return_value=[]):
        result = agent.run("a")
    assert result == []


def test_run_accepts_exactly_500_nonws_chars(db_session):
    agent = _make_agent(db_session)
    niche = "a" * 500
    with patch.object(agent, "_web_search", return_value=[]):
        result = agent.run(niche)
    assert result == []


# ── Web search fallback ───────────────────────────────────────────────────────

def test_web_search_returns_empty_on_import_error(db_session):
    agent = _make_agent(db_session)
    with patch("builtins.__import__", side_effect=ImportError):
        results = agent._web_search("test")
    assert results == []


# ── Ollama extraction happy path ──────────────────────────────────────────────

def test_extract_with_ollama_parses_json_from_response(db_session):
    agent = _make_agent(db_session)
    payload = {
        "company_name": "AcmeCorp",
        "contact_name": "Alice",
        "email": "alice@acmecorp.com",
        "linkedin_url": "https://linkedin.com/company/acmecorp",
        "has_job_posting": True,
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": json.dumps(payload)}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp):
        result = agent._extract_with_ollama("<html>...</html>", "SaaS")

    assert result["email"] == "alice@acmecorp.com"
    assert result["has_job_posting"] is True


def test_extract_with_ollama_returns_none_on_missing_json(db_session):
    agent = _make_agent(db_session)
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "I cannot determine the company."}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp):
        result = agent._extract_with_ollama("<html>...</html>", "SaaS")

    assert result is None


def test_extract_with_ollama_raises_on_timeout(db_session):
    import requests as req

    agent = _make_agent(db_session)
    with patch("requests.post", side_effect=req.exceptions.Timeout("timeout")):
        with pytest.raises(req.exceptions.Timeout):
            agent._extract_with_ollama("<html>", "SaaS")


# ── Regex extraction fallback ─────────────────────────────────────────────────

def test_extract_with_regex_extracts_email(db_session):
    agent = _make_agent(db_session)
    html = "<p>Contact us at support@example.com</p>"
    result = agent._extract_with_regex(html, "https://example.com")
    assert result is not None
    assert result["email"] == "support@example.com"


def test_extract_with_regex_extracts_linkedin(db_session):
    agent = _make_agent(db_session)
    html = '<a href="https://linkedin.com/company/testco">LinkedIn</a>'
    result = agent._extract_with_regex(html, "https://example.com")
    assert result is not None
    assert "linkedin.com/company/testco" in result["linkedin_url"]


def test_extract_with_regex_detects_job_posting(db_session):
    agent = _make_agent(db_session)
    html = "<p>We're hiring engineers! contact@company.com</p>"
    result = agent._extract_with_regex(html, "https://company.com")
    assert result is not None
    assert result["has_job_posting"] is True


def test_extract_with_regex_returns_none_when_no_usable_fields(db_session):
    agent = _make_agent(db_session)
    html = "<p>Hello world no email no title</p>"
    result = agent._extract_with_regex(html, "https://example.com")
    assert result is None


# ── Intent score ──────────────────────────────────────────────────────────────

def test_intent_score_all_signals(db_session):
    agent = _make_agent(db_session)
    score = agent._compute_intent_score({
        "job_posting_match": True,
        "email_resolved": True,
        "homepage_ok": True,
        "name_in_results": True,
    })
    assert score == 100


def test_intent_score_no_signals(db_session):
    agent = _make_agent(db_session)
    score = agent._compute_intent_score({})
    assert score == 0


def test_intent_score_job_posting_only(db_session):
    agent = _make_agent(db_session)
    score = agent._compute_intent_score({"job_posting_match": True})
    assert score == 30


def test_intent_score_email_resolved_only(db_session):
    agent = _make_agent(db_session)
    score = agent._compute_intent_score({"email_resolved": True})
    assert score == 20


def test_intent_score_capped_at_100(db_session):
    agent = _make_agent(db_session)
    # All signals sum to 100; adding a fictional 5th signal won't exceed 100
    score = agent._compute_intent_score({
        "job_posting_match": True,
        "email_resolved": True,
        "homepage_ok": True,
        "name_in_results": True,
        "extra_signal": True,  # ignored
    })
    assert score == 100


# ── Deduplication / persistence ───────────────────────────────────────────────

def test_persist_inserts_new_lead_with_email(db_session):
    from agents.outreach.enrichment_agent import Prospect
    from backend.db.models import Lead
    from unittest.mock import patch

    agent = _make_agent(db_session)
    p = Prospect(
        company_name="TestCo",
        contact_name="Bob",
        email="bob@testco.com",
        website="https://testco.com",
        intent_score=60,
    )
    with patch("backend.services.event_bus.event_bus.publish"):
        result = agent._persist_prospect(p)

    assert result is True
    lead = db_session.query(Lead).filter(Lead.email == "bob@testco.com").first()
    assert lead is not None
    assert lead.company == "TestCo"


def test_persist_updates_existing_lead_with_same_email(db_session):
    from agents.outreach.enrichment_agent import Prospect
    from backend.db.models import Lead
    from unittest.mock import patch

    # Insert existing lead
    existing = Lead(email="bob@testco.com", name="Bob Old", company="OldCo")
    db_session.add(existing)
    db_session.commit()

    agent = _make_agent(db_session)
    p = Prospect(
        company_name="NewCo",
        contact_name="Bob New",
        email="bob@testco.com",
        website="https://newco.com",
        intent_score=80,
    )
    with patch("backend.services.event_bus.event_bus.publish"):
        result = agent._persist_prospect(p)

    assert result is True
    leads = db_session.query(Lead).filter(Lead.email == "bob@testco.com").all()
    assert len(leads) == 1
    assert leads[0].company == "NewCo"


def test_persist_always_inserts_null_email(db_session):
    from agents.outreach.enrichment_agent import Prospect
    from backend.db.models import Lead
    from unittest.mock import patch

    agent = _make_agent(db_session)
    for _ in range(2):
        p = Prospect(company_name="AnonCo", email=None, needs_review=True)
        with patch("backend.services.event_bus.event_bus.publish"):
            agent._persist_prospect(p)

    # Two distinct records for null-email prospects
    leads = db_session.query(Lead).filter(Lead.email.is_(None)).all()
    assert len(leads) == 2


def test_persist_sets_needs_review_for_null_email(db_session):
    from agents.outreach.enrichment_agent import Prospect
    from backend.db.models import Lead
    from unittest.mock import patch

    agent = _make_agent(db_session)
    p = Prospect(company_name="AnonCo", email=None)
    with patch("backend.services.event_bus.event_bus.publish"):
        agent._persist_prospect(p)

    lead = db_session.query(Lead).filter(Lead.email.is_(None)).first()
    assert lead.needs_review is True


# ── Ollama fallback path (integration of _extract_entities) ──────────────────

def test_extract_entities_falls_back_to_regex_on_ollama_failure(db_session):
    import requests as req

    agent = _make_agent(db_session)
    html = "<title>FallbackCo</title><p>contact@fallback.com</p>"

    with patch("requests.post", side_effect=req.exceptions.ConnectionError("refused")):
        result = agent._extract_entities(html, "niche", "https://fallback.com")

    assert result is not None
    assert result["email"] == "contact@fallback.com"


def test_extract_entities_returns_none_when_both_methods_yield_nothing(db_session):
    import requests as req

    agent = _make_agent(db_session)
    html = "<p>no useful content</p>"

    with patch("requests.post", side_effect=req.exceptions.ConnectionError("refused")):
        result = agent._extract_entities(html, "niche", "https://empty.com")

    assert result is None
