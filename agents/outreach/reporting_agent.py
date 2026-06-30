"""
Reporting Agent — aggregates daily outreach metrics and exposes them via API.

Computes metrics for the preceding UTC calendar day:
  prospects_discovered  — count of leads inserted that day
  emails_sent           — count of SequenceStepLog rows with outcome='sent'
  open_rate             — opens / sent (null if no trackable sends)
  reply_rate            — replied enrollments / sent (null if sent == 0)
  interested_count      — enrollments with status = 'replied_interested'
  bounce_rate           — bounced enrollments / sent (null if sent == 0)

Results are upserted into ``outreach_daily_metrics`` ensuring idempotency.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

logger = logging.getLogger("ReportingAgent")


class ReportingAgent:
    """
    Aggregates and persists daily outreach metrics.

    Parameters
    ----------
    db_session:
        Optional SQLAlchemy ``Session``.
    """

    def __init__(self, db_session=None) -> None:
        self._db = db_session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_daily_report(self, report_date: Optional[date] = None) -> dict:
        """
        Compute and upsert metrics for ``report_date`` (default: yesterday UTC).

        Returns
        -------
        dict
            Metric snapshot for the date.
        """
        if report_date is None:
            report_date = (datetime.utcnow() - timedelta(days=1)).date()

        metrics = self._compute_metrics(report_date)

        db = self._get_db()
        try:
            self._upsert_metrics(db, report_date, metrics)
        finally:
            self._maybe_close(db)

        return metrics

    def get_metrics_range(self, start_date: date, end_date: date) -> list[dict]:
        """
        Fetch persisted daily metrics for a date range (inclusive).

        Returns an empty list if no data exists.
        """
        from backend.db.models_outreach import OutreachDailyMetrics

        db = self._get_db()
        try:
            rows = (
                db.query(OutreachDailyMetrics)
                .filter(
                    OutreachDailyMetrics.date >= start_date,
                    OutreachDailyMetrics.date <= end_date,
                )
                .all()
            )
            # Group by date into a nested dict, then flatten to a list of day-dicts.
            by_date: dict[date, dict] = {}
            for row in rows:
                d = row.date
                if d not in by_date:
                    by_date[d] = {"date": d.isoformat()}
                by_date[d][row.metric_name] = row.metric_value
            return sorted(by_date.values(), key=lambda x: x["date"])
        finally:
            self._maybe_close(db)

    # ------------------------------------------------------------------
    # Metric computation
    # ------------------------------------------------------------------

    def _compute_metrics(self, report_date: date) -> dict:
        """Compute all six metrics for ``report_date``."""
        from backend.db.models import Lead
        from backend.db.models_outreach import (
            SequenceEnrollment,
            SequenceStepLog,
        )

        db = self._get_db()
        try:
            # Day boundary in UTC
            day_start = datetime(report_date.year, report_date.month, report_date.day, 0, 0, 0)
            day_end = day_start + timedelta(days=1)

            # prospects_discovered
            prospects_discovered = (
                db.query(Lead)
                .filter(Lead.created_at >= day_start, Lead.created_at < day_end)
                .count()
            )

            # emails_sent
            sent_logs = (
                db.query(SequenceStepLog)
                .filter(
                    SequenceStepLog.outcome == "sent",
                    SequenceStepLog.sent_at >= day_start,
                    SequenceStepLog.sent_at < day_end,
                )
                .all()
            )
            emails_sent = len(sent_logs)

            # open_rate — based on opens_tracked logs
            trackable = [l for l in sent_logs if l.opens_tracked]
            if trackable:
                opens = sum(1 for l in trackable if l.opened)
                open_rate: Optional[float] = opens / len(trackable)
            else:
                open_rate = None

            # reply_rate
            if emails_sent > 0:
                replied_enrollments = (
                    db.query(SequenceEnrollment)
                    .filter(
                        SequenceEnrollment.status.in_(
                            ["replied", "replied_interested", "replied_uninterested"]
                        ),
                        SequenceEnrollment.updated_at >= day_start,
                        SequenceEnrollment.updated_at < day_end,
                    )
                    .count()
                )
                reply_rate: Optional[float] = replied_enrollments / emails_sent
            else:
                reply_rate = None

            # interested_count
            interested_count = (
                db.query(SequenceEnrollment)
                .filter(
                    SequenceEnrollment.status == "replied_interested",
                    SequenceEnrollment.updated_at >= day_start,
                    SequenceEnrollment.updated_at < day_end,
                )
                .count()
            )

            # bounce_rate
            if emails_sent > 0:
                bounced = (
                    db.query(SequenceEnrollment)
                    .filter(
                        SequenceEnrollment.status == "failed",
                        SequenceEnrollment.updated_at >= day_start,
                        SequenceEnrollment.updated_at < day_end,
                    )
                    .count()
                )
                bounce_rate: Optional[float] = bounced / emails_sent
            else:
                bounce_rate = None

            return {
                "prospects_discovered": prospects_discovered,
                "emails_sent": emails_sent,
                "open_rate": open_rate,
                "reply_rate": reply_rate,
                "interested_count": interested_count,
                "bounce_rate": bounce_rate,
            }
        finally:
            self._maybe_close(db)

    def _upsert_metrics(self, db, report_date: date, metrics: dict) -> None:
        """Insert or update each metric row for the given date (idempotent)."""
        from backend.db.models_outreach import OutreachDailyMetrics

        for metric_name, metric_value in metrics.items():
            existing = (
                db.query(OutreachDailyMetrics)
                .filter(
                    OutreachDailyMetrics.date == report_date,
                    OutreachDailyMetrics.metric_name == metric_name,
                )
                .first()
            )
            if existing:
                existing.metric_value = metric_value
                existing.updated_at = datetime.utcnow()
            else:
                row = OutreachDailyMetrics(
                    id=str(uuid.uuid4()),
                    date=report_date,
                    metric_name=metric_name,
                    metric_value=metric_value,
                )
                db.add(row)
        db.commit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_db(self):
        if self._db is not None:
            return self._db
        from backend.db.session import SessionLocal

        return SessionLocal()

    def _maybe_close(self, db) -> None:
        if self._db is None:
            db.close()
