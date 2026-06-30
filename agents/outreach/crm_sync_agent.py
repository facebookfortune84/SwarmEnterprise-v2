"""
CRM Sync Agent — keeps the internal Lead table and Ticket system consistent
with the state of the outreach pipeline.

Listens to the following EventBus events:
  prospect_discovered  → upsert Lead with status NEW
  sequence_enrolled    → update Lead status to CONTACTED
  email_sent           → (no-op; future: track email count)
  reply_received       → update Lead to QUALIFIED + create Ticket (interested)
                         update Lead to COLD_REJECTED (not_interested)
  sequence_completed   → update Lead to COLD (no reply)

Out-of-order events are buffered (up to 50 per lead) until the
``prospect_discovered`` event arrives and can replay them.

The agent is registered on EventBus at startup via ``register()``.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Callable

logger = logging.getLogger("CRMSyncAgent")

# Maximum buffered events per lead to prevent unbounded memory growth.
_MAX_BUFFER = 50


class CRMSyncAgent:
    """
    Event-driven CRM state machine.

    Parameters
    ----------
    db_session:
        Optional SQLAlchemy ``Session``.  A new session is opened per
        handler invocation if not provided.
    """

    def __init__(self, db_session=None) -> None:
        self._db = db_session
        # Keyed by lead_id → list of (event_type, payload) pairs
        self._pending_buffer: dict[str, list[tuple[str, dict]]] = defaultdict(list)

    # ------------------------------------------------------------------
    # EventBus registration
    # ------------------------------------------------------------------

    def register(self) -> None:
        """Subscribe all handlers to the application EventBus."""
        from backend.services.event_bus import event_bus

        event_bus.subscribe("prospect_discovered", self.handle_prospect_discovered)
        event_bus.subscribe("sequence_enrolled", self.handle_sequence_enrolled)
        event_bus.subscribe("email_sent", self.handle_email_sent)
        event_bus.subscribe("reply_received", self.handle_reply_received)
        event_bus.subscribe("sequence_completed", self.handle_sequence_completed)
        logger.info("CRMSyncAgent registered all event handlers.")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def handle_prospect_discovered(self, payload: dict) -> None:
        """Upsert the Lead with status NEW, then replay buffered events."""
        from backend.db.models import Lead

        lead_id = payload.get("lead_id", "")
        if not lead_id:
            logger.warning("prospect_discovered event missing lead_id — discarding.")
            return

        db = self._get_db()
        try:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if lead:
                if lead.status in (None, ""):
                    lead.status = "NEW"
                    db.commit()
            else:
                new_lead = Lead(
                    id=lead_id,
                    email=payload.get("email"),
                    name=payload.get("contact_name", ""),
                    company=payload.get("company", ""),
                    status="NEW",
                )
                db.add(new_lead)
                db.commit()

            self._record_timeline(db, lead_id, None, "NEW", "prospect_discovered")

        except Exception as exc:
            logger.error("handle_prospect_discovered failed: %s", exc)
            db.rollback()
            return
        finally:
            self._maybe_close(db)

        # Replay buffered events for this lead
        buffered = list(self._pending_buffer.pop(lead_id, []))
        for event_type, buffered_payload in buffered:
            handler = self._handler_for(event_type)
            if handler:
                handler(buffered_payload)

    def handle_sequence_enrolled(self, payload: dict) -> None:
        """Update Lead status to CONTACTED."""
        from backend.db.models import Lead

        lead_id = payload.get("lead_id", "")
        if not lead_id:
            return

        db = self._get_db()
        try:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if lead is None:
                if len(self._pending_buffer[lead_id]) < _MAX_BUFFER:
                    self._pending_buffer[lead_id].append(("sequence_enrolled", payload))
                logger.warning(
                    "sequence_enrolled: lead %s not found — buffering event.", lead_id
                )
                return
            from_status = lead.status
            lead.status = "CONTACTED"
            db.commit()
            self._record_timeline(db, lead_id, from_status, "CONTACTED", "sequence_enrolled")
        except Exception as exc:
            logger.error("handle_sequence_enrolled failed: %s", exc)
            db.rollback()
        finally:
            self._maybe_close(db)

    def handle_email_sent(self, payload: dict) -> None:
        """No-op placeholder — future: increment email count on lead."""
        logger.debug("email_sent event for lead %s.", payload.get("lead_id"))

    def handle_reply_received(self, payload: dict) -> None:
        """
        Update Lead status based on reply classification.

        - ``interested`` → QUALIFIED + create high-priority Ticket (atomic).
        - ``not_interested`` → COLD_REJECTED.
        """
        from backend.db.models import Lead

        lead_id = payload.get("lead_id", "")
        classification = payload.get("classification", "")
        if not lead_id:
            return

        db = self._get_db()
        try:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if lead is None:
                logger.warning(
                    "reply_received: lead %s not found — discarding.", lead_id
                )
                return

            from_status = lead.status

            if classification == "interested":
                # Atomic: update Lead + create Ticket in one transaction
                lead.status = "QUALIFIED"
                try:
                    from backend.services.ticket_service import TicketService

                    ts = TicketService(db)
                    ts.create_ticket(
                        title=f"Qualified lead: {lead.company or lead.email}",
                        instruction=f"Lead {lead.id} replied as interested.",
                        priority="high",
                        tags="crm,qualified",
                    )
                    db.commit()
                    self._record_timeline(
                        db, lead_id, from_status, "QUALIFIED", "reply_received"
                    )
                except Exception as inner:
                    logger.error(
                        "Atomic QUALIFIED + Ticket transaction failed for lead %s: %s",
                        lead_id,
                        inner,
                    )
                    db.rollback()

            elif classification == "not_interested":
                lead.status = "COLD_REJECTED"
                db.commit()
                self._record_timeline(
                    db, lead_id, from_status, "COLD_REJECTED", "reply_received"
                )

        except Exception as exc:
            logger.error("handle_reply_received failed: %s", exc)
            db.rollback()
        finally:
            self._maybe_close(db)

    def handle_sequence_completed(self, payload: dict) -> None:
        """Update Lead to COLD when a sequence completes without a reply."""
        from backend.db.models import Lead

        lead_id = payload.get("lead_id", "")
        has_reply = payload.get("has_reply", False)
        if not lead_id:
            return
        if has_reply:
            return  # Reply already handled by handle_reply_received

        db = self._get_db()
        try:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if lead is None:
                logger.warning(
                    "sequence_completed: lead %s not found — discarding.", lead_id
                )
                return
            from_status = lead.status
            lead.status = "COLD"
            db.commit()
            self._record_timeline(db, lead_id, from_status, "COLD", "sequence_completed")
        except Exception as exc:
            logger.error("handle_sequence_completed failed: %s", exc)
            db.rollback()
        finally:
            self._maybe_close(db)

    # ------------------------------------------------------------------
    # Lead timeline
    # ------------------------------------------------------------------

    def _record_timeline(
        self,
        db,
        lead_id: str,
        from_status: "str | None",
        to_status: str,
        triggered_by: str,
    ) -> None:
        from backend.db.models_outreach import LeadTimeline

        try:
            entry = LeadTimeline(
                id=str(uuid.uuid4()),
                lead_id=lead_id,
                from_status=from_status,
                to_status=to_status,
                triggered_by=triggered_by,
                occurred_at=datetime.utcnow(),
            )
            db.add(entry)
            db.commit()
        except Exception as exc:
            logger.warning("Could not record timeline entry: %s", exc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _handler_for(self, event_type: str) -> "Callable | None":
        return {
            "sequence_enrolled": self.handle_sequence_enrolled,
            "email_sent": self.handle_email_sent,
            "reply_received": self.handle_reply_received,
            "sequence_completed": self.handle_sequence_completed,
        }.get(event_type)

    def _get_db(self):
        if self._db is not None:
            return self._db
        from backend.db.session import SessionLocal

        return SessionLocal()

    def _maybe_close(self, db) -> None:
        if self._db is None:
            db.close()


# Module-level singleton — import-safe; only activates on explicit register() call.
crm_sync_agent = CRMSyncAgent()
