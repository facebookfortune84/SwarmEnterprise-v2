"""
Sequencer Agent — multi-step email sequence engine.

Responsibilities
----------------
1. Create and validate Sequence definitions.
2. Enrol prospects into sequences (rejecting duplicate active enrolments).
3. Render personalised email templates (merge-field substitution).
4. Process due sequence steps: compute scheduled send times, call
   EmailTools.send_email(), and record outcomes.
5. Halt enrollments when a ``reply_received`` event arrives on the EventBus.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("SequencerAgent")

# Merge-field pattern used in templates.
_MERGE_FIELD_RE = re.compile(r"\{\{([a-z_]+)\}\}")

# Supported merge fields.
_SUPPORTED_FIELDS = {"first_name", "last_name", "company", "website"}


class SequencerAgent:
    """
    Manages sequence definitions, enrolments, and step processing.

    Parameters
    ----------
    db_session:
        Optional SQLAlchemy ``Session``.  A fresh session is opened when
        needed if omitted.
    """

    def __init__(self, db_session=None) -> None:
        self._db = db_session

    # ------------------------------------------------------------------
    # Sequence CRUD
    # ------------------------------------------------------------------

    def create_sequence(self, payload: dict) -> object:
        """
        Validate and persist a new Sequence definition.

        Parameters
        ----------
        payload:
            dict with keys: ``name`` (str), ``steps`` (list), ``status``
            (optional str, default "active").

        Returns
        -------
        Sequence ORM object.

        Raises
        ------
        ValueError
            If payload fails validation.
        """
        from backend.db.models_outreach import Sequence

        name = payload.get("name", "")
        if not (1 <= len(name) <= 255):
            raise ValueError("Sequence name must be 1–255 characters.")

        steps = payload.get("steps", [])
        if not (1 <= len(steps) <= 10):
            raise ValueError("Sequence must have 1–10 steps.")

        for i, step in enumerate(steps):
            delay = step.get("delay_days")
            if not isinstance(delay, int) or not (0 <= delay <= 365):
                raise ValueError(f"Step {i}: delay_days must be integer 0–365.")
            if not step.get("subject_template", "").strip():
                raise ValueError(f"Step {i}: subject_template must not be empty.")
            if not step.get("body_template", "").strip():
                raise ValueError(f"Step {i}: body_template must not be empty.")

        allowed_statuses = {"active", "paused", "archived"}
        status = payload.get("status", "active")
        if status not in allowed_statuses:
            raise ValueError(f"status must be one of {allowed_statuses}.")

        db = self._get_db()
        try:
            seq = Sequence(
                id=str(uuid.uuid4()),
                name=name,
                steps_json=json.dumps(steps),
                status=status,
            )
            db.add(seq)
            db.commit()
            db.refresh(seq)
            return seq
        finally:
            self._maybe_close(db)

    # ------------------------------------------------------------------
    # Enrolment
    # ------------------------------------------------------------------

    def enroll_prospect(self, lead_id: str, sequence_id: str) -> object:
        """
        Enrol a lead in a sequence.

        Raises
        ------
        ValueError
            If an active enrolment already exists for this lead + sequence.
        """
        from backend.db.models_outreach import SequenceEnrollment

        db = self._get_db()
        try:
            existing = (
                db.query(SequenceEnrollment)
                .filter(
                    SequenceEnrollment.lead_id == lead_id,
                    SequenceEnrollment.sequence_id == sequence_id,
                    SequenceEnrollment.status == "active",
                )
                .first()
            )
            if existing:
                raise ValueError(
                    f"Lead {lead_id} already has an active enrollment in "
                    f"sequence {sequence_id}. Enrollment id: {existing.id}."
                )
            enrollment = SequenceEnrollment(
                id=str(uuid.uuid4()),
                lead_id=lead_id,
                sequence_id=sequence_id,
                status="active",
                current_step=0,
                enrolled_at=datetime.utcnow(),
            )
            db.add(enrollment)
            db.commit()
            db.refresh(enrollment)
            return enrollment
        finally:
            self._maybe_close(db)

    # ------------------------------------------------------------------
    # Template rendering
    # ------------------------------------------------------------------

    def render_template(self, template: str, prospect: dict) -> str:
        """
        Substitute ``{{first_name}}``, ``{{last_name}}``, ``{{company}}``,
        and ``{{website}}`` from the prospect dict.

        Null or missing prospect fields become empty strings.  Any
        unsupported ``{{token}}`` is also replaced with an empty string
        so that no raw merge tokens appear in the output.
        """

        def replacer(match: re.Match) -> str:
            field = match.group(1)
            value = prospect.get(field) or ""
            return str(value)

        return _MERGE_FIELD_RE.sub(replacer, template)

    # ------------------------------------------------------------------
    # Step processing (called by the Celery Beat task)
    # ------------------------------------------------------------------

    def process_due_steps(self) -> int:
        """
        Find all active enrollments with a step that is now due and
        attempt to send the corresponding email.

        Returns the number of steps processed.
        """
        from backend.db.models_outreach import Sequence, SequenceEnrollment, SequenceStepLog
        from backend.db.models import Lead
        from agents.outreach.email_engine import EmailTools

        db = self._get_db()
        email_tools = EmailTools()
        processed = 0

        try:
            enrollments = (
                db.query(SequenceEnrollment)
                .filter(SequenceEnrollment.status == "active")
                .all()
            )
            for enrollment in enrollments:
                sequence = db.query(Sequence).filter(
                    Sequence.id == enrollment.sequence_id
                ).first()
                if not sequence:
                    continue

                steps = json.loads(sequence.steps_json or "[]")
                step_idx = enrollment.current_step
                if step_idx >= len(steps):
                    # Sequence complete
                    enrollment.status = "completed"
                    db.commit()
                    continue

                # Compute scheduled send time
                enrolled_at: datetime = enrollment.enrolled_at
                total_delay_days = sum(s.get("delay_days", 0) for s in steps[: step_idx + 1])
                scheduled_at = enrolled_at + timedelta(days=total_delay_days)

                if datetime.utcnow() < scheduled_at:
                    continue  # Not due yet

                step = steps[step_idx]

                # Fetch lead for personalisation
                lead = db.query(Lead).filter(Lead.id == enrollment.lead_id).first()
                if not lead or not lead.email:
                    continue

                prospect_dict = {
                    "first_name": (lead.name or "").split()[0] if lead.name else "",
                    "last_name": " ".join((lead.name or "").split()[1:]) if lead.name else "",
                    "company": lead.company or "",
                    "website": getattr(lead, "website", "") or "",
                }

                subject = self.render_template(step.get("subject_template", ""), prospect_dict)
                body = self.render_template(step.get("body_template", ""), prospect_dict)

                result = email_tools.send_email(lead.email, subject, body)

                if "ERROR" in str(result):
                    log = SequenceStepLog(
                        id=str(uuid.uuid4()),
                        enrollment_id=enrollment.id,
                        step_index=step_idx,
                        outcome="failed",
                        scheduled_at=scheduled_at,
                        error_message=str(result),
                    )
                    db.add(log)
                    enrollment.status = "paused"
                    db.commit()
                else:
                    log = SequenceStepLog(
                        id=str(uuid.uuid4()),
                        enrollment_id=enrollment.id,
                        step_index=step_idx,
                        outcome="sent",
                        scheduled_at=scheduled_at,
                        sent_at=datetime.utcnow(),
                    )
                    db.add(log)
                    enrollment.current_step = step_idx + 1
                    db.commit()
                    processed += 1

        finally:
            self._maybe_close(db)

        return processed

    # ------------------------------------------------------------------
    # Reply-halt (EventBus subscriber)
    # ------------------------------------------------------------------

    def on_reply_received(self, payload: dict) -> None:
        """
        Halt all remaining steps for the given lead's active enrollment.

        This method is registered with the EventBus on agent startup.
        """
        from backend.db.models_outreach import SequenceEnrollment

        lead_id = payload.get("lead_id")
        if not lead_id:
            return

        db = self._get_db()
        try:
            enrollments = (
                db.query(SequenceEnrollment)
                .filter(
                    SequenceEnrollment.lead_id == lead_id,
                    SequenceEnrollment.status == "active",
                )
                .all()
            )
            for enrollment in enrollments:
                enrollment.status = "replied"
            db.commit()
            logger.info("Halted %d enrollment(s) for lead %s.", len(enrollments), lead_id)
        finally:
            self._maybe_close(db)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_db(self):
        if self._db is not None:
            return self._db
        from backend.db.session import SessionLocal

        return SessionLocal()

    def _maybe_close(self, db) -> None:
        if self._db is None:
            db.close()
