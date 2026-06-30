"""
Unit tests for the ReportingAgent.

SQLAlchemy session replaced with in-memory SQLite.
Covers all six metric computations, null cases, and upsert idempotency.
"""

from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timedelta
from unittest.mock import patch

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
    from agents.outreach.reporting_agent import ReportingAgent
    return ReportingAgent(db_session=db)


def _today():
    return date.today()


def _yesterday():
    return (datetime.utcnow() - timedelta(days=1)).date()


# ── Empty database metrics ────────────────────────────────────────────────────

def test_metrics_all_zero_on_empty_db(db_session):
    agent = _make_agent(db_session)
    metrics = agent._compute_metrics(_yesterday())
    assert metrics["prospects_discovered"] == 0
    assert metrics["emails_sent"] == 0
    assert metrics["open_rate"] is None
    assert metrics["reply_rate"] is None
    assert metrics["interested_count"] == 0
    assert metrics["bounce_rate"] is None


# ── prospects_discovered ──────────────────────────────────────────────────────

def test_metrics_counts_leads_created_yesterday(db_session):
    from backend.db.models import Lead

    yesterday = _yesterday()
    day_start = datetime(yesterday.year, yesterday.month, yesterday.day, 6, 0, 0)

    for _ in range(3):
        lead = Lead(
            id=str(uuid.uuid4()),
            email=f"{uuid.uuid4().hex[:6]}@example.com",
            status="NEW",
            created_at=day_start,
        )
        db_session.add(lead)
    db_session.commit()

    agent = _make_agent(db_session)
    metrics = agent._compute_metrics(yesterday)
    assert metrics["prospects_discovered"] == 3


# ── emails_sent ───────────────────────────────────────────────────────────────

def test_metrics_counts_sent_logs(db_session):
    from backend.db.models import Lead
    from backend.db.models_outreach import Sequence, SequenceEnrollment, SequenceStepLog

    yesterday = _yesterday()
    sent_at = datetime(yesterday.year, yesterday.month, yesterday.day, 10, 0, 0)

    lead = Lead(id=str(uuid.uuid4()), email="s@example.com", status="CONTACTED")
    seq = Sequence(id=str(uuid.uuid4()), name="S", steps_json="[]", status="active")
    db_session.add_all([lead, seq])
    db_session.commit()

    enrollment = SequenceEnrollment(
        id=str(uuid.uuid4()),
        lead_id=lead.id,
        sequence_id=seq.id,
        status="active",
        current_step=1,
        enrolled_at=datetime.utcnow(),
    )
    db_session.add(enrollment)
    db_session.commit()

    for _ in range(2):
        log = SequenceStepLog(
            id=str(uuid.uuid4()),
            enrollment_id=enrollment.id,
            step_index=0,
            outcome="sent",
            sent_at=sent_at,
        )
        db_session.add(log)
    db_session.commit()

    agent = _make_agent(db_session)
    metrics = agent._compute_metrics(yesterday)
    assert metrics["emails_sent"] == 2


# ── open_rate ─────────────────────────────────────────────────────────────────

def test_metrics_open_rate_when_trackable(db_session):
    from backend.db.models import Lead
    from backend.db.models_outreach import Sequence, SequenceEnrollment, SequenceStepLog

    yesterday = _yesterday()
    sent_at = datetime(yesterday.year, yesterday.month, yesterday.day, 10, 0, 0)

    lead = Lead(id=str(uuid.uuid4()), email="or@example.com", status="CONTACTED")
    seq = Sequence(id=str(uuid.uuid4()), name="S", steps_json="[]", status="active")
    db_session.add_all([lead, seq])
    db_session.commit()

    enrollment = SequenceEnrollment(
        id=str(uuid.uuid4()), lead_id=lead.id, sequence_id=seq.id,
        status="active", current_step=1, enrolled_at=datetime.utcnow(),
    )
    db_session.add(enrollment)
    db_session.commit()

    # 2 sent with tracking; 1 opened
    log1 = SequenceStepLog(
        id=str(uuid.uuid4()), enrollment_id=enrollment.id,
        step_index=0, outcome="sent", sent_at=sent_at,
        opens_tracked=True, opened=True,
    )
    log2 = SequenceStepLog(
        id=str(uuid.uuid4()), enrollment_id=enrollment.id,
        step_index=1, outcome="sent", sent_at=sent_at,
        opens_tracked=True, opened=False,
    )
    db_session.add_all([log1, log2])
    db_session.commit()

    agent = _make_agent(db_session)
    metrics = agent._compute_metrics(yesterday)
    assert metrics["open_rate"] == pytest.approx(0.5)


def test_metrics_open_rate_null_when_no_trackable(db_session):
    from backend.db.models import Lead
    from backend.db.models_outreach import Sequence, SequenceEnrollment, SequenceStepLog

    yesterday = _yesterday()
    sent_at = datetime(yesterday.year, yesterday.month, yesterday.day, 10, 0, 0)

    lead = Lead(id=str(uuid.uuid4()), email="nt@example.com", status="CONTACTED")
    seq = Sequence(id=str(uuid.uuid4()), name="S", steps_json="[]", status="active")
    db_session.add_all([lead, seq])
    db_session.commit()

    enrollment = SequenceEnrollment(
        id=str(uuid.uuid4()), lead_id=lead.id, sequence_id=seq.id,
        status="active", current_step=1, enrolled_at=datetime.utcnow(),
    )
    db_session.add(enrollment)
    db_session.commit()

    log = SequenceStepLog(
        id=str(uuid.uuid4()), enrollment_id=enrollment.id,
        step_index=0, outcome="sent", sent_at=sent_at,
        opens_tracked=False,
    )
    db_session.add(log)
    db_session.commit()

    agent = _make_agent(db_session)
    metrics = agent._compute_metrics(yesterday)
    assert metrics["open_rate"] is None


# ── reply_rate and bounce_rate null when sent == 0 ────────────────────────────

def test_metrics_reply_and_bounce_rate_null_when_no_sends(db_session):
    agent = _make_agent(db_session)
    metrics = agent._compute_metrics(_yesterday())
    assert metrics["reply_rate"] is None
    assert metrics["bounce_rate"] is None


# ── Upsert idempotency ────────────────────────────────────────────────────────

def test_generate_daily_report_is_idempotent(db_session):
    from backend.db.models_outreach import OutreachDailyMetrics

    agent = _make_agent(db_session)
    report_date = _yesterday()

    # Run twice
    agent.generate_daily_report(report_date)
    agent.generate_daily_report(report_date)

    rows = (
        db_session.query(OutreachDailyMetrics)
        .filter(OutreachDailyMetrics.date == report_date)
        .all()
    )
    metric_names = [r.metric_name for r in rows]
    # Each metric should appear exactly once
    assert len(metric_names) == len(set(metric_names))


# ── get_metrics_range ─────────────────────────────────────────────────────────

def test_get_metrics_range_returns_empty_on_no_data(db_session):
    agent = _make_agent(db_session)
    result = agent.get_metrics_range(date(2020, 1, 1), date(2020, 1, 7))
    assert result == []


def test_get_metrics_range_returns_data_in_date_order(db_session):
    agent = _make_agent(db_session)
    d1 = date(2024, 1, 1)
    d2 = date(2024, 1, 2)
    agent.generate_daily_report(d1)
    agent.generate_daily_report(d2)

    result = agent.get_metrics_range(d1, d2)
    assert len(result) == 2
    assert result[0]["date"] < result[1]["date"]
