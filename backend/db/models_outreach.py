"""
SQLAlchemy models for the outreach pipeline.

Covers:
- Sequence / SequenceStep definitions
- SequenceEnrollment (prospect ↔ sequence state machine)
- SequenceStepLog (per-step execution records)
- OutreachDailyMetrics (aggregated daily reporting table)
- LeadTimeline (audit trail of lead status transitions)
- ProcessedEmailUID (dedup table for IMAP reply processing)
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Boolean,
    Integer,
    Float,
    Date,
    UniqueConstraint,
    ForeignKey,
)

from backend.db.base import Base


class Sequence(Base):
    """Outreach email sequence definition."""

    __tablename__ = "sequences"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    # JSON array of {delay_days, subject_template, body_template}
    steps_json = Column(Text, nullable=False, default="[]")
    # active / paused / archived
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SequenceEnrollment(Base):
    """Links a prospect (Lead) to a Sequence and tracks progress."""

    __tablename__ = "sequence_enrollments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False, index=True)
    sequence_id = Column(String, ForeignKey("sequences.id"), nullable=False, index=True)
    # active / paused / replied / replied_interested / replied_uninterested / failed / completed
    status = Column(String(32), nullable=False, default="active")
    current_step = Column(Integer, nullable=False, default=0)
    enrolled_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "lead_id",
            "sequence_id",
            name="uq_enrollment_lead_sequence",
        ),
    )


class SequenceStepLog(Base):
    """Immutable record of one step execution for an enrollment."""

    __tablename__ = "sequence_step_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    enrollment_id = Column(
        String, ForeignKey("sequence_enrollments.id"), nullable=False, index=True
    )
    step_index = Column(Integer, nullable=False)
    # sent / failed
    outcome = Column(String(16), nullable=False)
    # True when open-tracking pixel was included
    opens_tracked = Column(Boolean, default=False)
    # True when an open event was recorded
    opened = Column(Boolean, default=False)
    scheduled_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class OutreachDailyMetrics(Base):
    """Aggregated daily outreach metrics for the reporting dashboard."""

    __tablename__ = "outreach_daily_metrics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    date = Column(Date, nullable=False)
    metric_name = Column(String(64), nullable=False)
    metric_value = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("date", "metric_name", name="uq_daily_metric_date_name"),
    )


class LeadTimeline(Base):
    """Audit trail of status transitions for a lead."""

    __tablename__ = "lead_timeline"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False, index=True)
    from_status = Column(String(32), nullable=True)
    to_status = Column(String(32), nullable=False)
    # Event type that triggered the transition, e.g. 'prospect_discovered'
    triggered_by = Column(String(64), nullable=False)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ProcessedEmailUID(Base):
    """IMAP message UIDs already handled by the Reply Handler Agent."""

    __tablename__ = "processed_email_uids"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # Composite key: mailbox + uid prevents cross-mailbox collisions.
    mailbox = Column(String(255), nullable=False)
    uid = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("mailbox", "uid", name="uq_processed_email_uid"),
    )
