"""
Reply Handler Agent — IMAP inbox polling and reply classification.

Poll an IMAP mailbox every N minutes, classify each unseen reply using Ollama
(with a rule-based heuristic fallback), and dispatch the appropriate downstream
actions (enrollment state machine updates, ticket creation, EventBus events).

IMAP credentials are read from environment variables:
  IMAP_SERVER   — hostname of the IMAP server
  IMAP_USER     — mailbox username / address
  IMAP_PASS     — mailbox password

Processed message UIDs are stored in ``processed_email_uids`` AFTER all
downstream actions complete, ensuring failed deliveries are retried on the
next poll cycle.
"""

from __future__ import annotations

import imaplib
import logging
import os
import re
import socket
import uuid
from datetime import datetime
from typing import Literal

logger = logging.getLogger("ReplyHandlerAgent")

ReplyClassification = Literal["interested", "not_interested", "auto_reply", "bounce"]

# Regex patterns for rule-based classification.
_BOUNCE_SUBJECT_RE = re.compile(
    r"^(Mail Delivery|Undeliverable|Delivery (Status Notification|Failed))",
    re.IGNORECASE,
)
_AUTO_REPLY_BODY_RE = re.compile(
    r"(out of office|on vacation|auto.?reply|automatic reply)",
    re.IGNORECASE,
)
_UNSUBSCRIBE_BODY_RE = re.compile(
    r"(unsubscribe|remove me)",
    re.IGNORECASE,
)


class EmailMessage:
    """Simple value object holding a fetched email's key fields."""

    __slots__ = ("uid", "sender", "subject", "body", "return_path")

    def __init__(
        self,
        uid: str,
        sender: str,
        subject: str,
        body: str,
        return_path: str = "",
    ) -> None:
        self.uid = uid
        self.sender = sender
        self.subject = subject
        self.body = body
        self.return_path = return_path


class ReplyHandlerAgent:
    """
    Polls an IMAP mailbox, classifies each unseen reply, and dispatches
    downstream actions.

    Parameters
    ----------
    db_session:
        Optional SQLAlchemy ``Session``.
    ollama_timeout:
        Seconds to wait for Ollama before falling back to heuristics.
    mailbox:
        IMAP folder to poll (default: "INBOX").
    """

    def __init__(
        self,
        db_session=None,
        ollama_timeout: float = 10.0,
        mailbox: str = "INBOX",
    ) -> None:
        self._db = db_session
        self._ollama_timeout = ollama_timeout
        self._mailbox = mailbox

    # ------------------------------------------------------------------
    # Public entry-point (called by Celery task)
    # ------------------------------------------------------------------

    def poll_inbox(self) -> int:
        """
        Connect to IMAP, fetch UNSEEN messages, classify each, dispatch
        downstream actions, and record processed UIDs.

        Returns the number of messages processed.
        """
        server = os.environ.get("IMAP_SERVER", "")
        user = os.environ.get("IMAP_USER", "")
        password = os.environ.get("IMAP_PASS", "")

        if not server or not user or not password:
            logger.warning(
                "IMAP_SERVER / IMAP_USER / IMAP_PASS not configured — skipping inbox poll."
            )
            return 0

        try:
            imap = imaplib.IMAP4_SSL(server)
            imap.login(user, password)
            imap.select(self._mailbox)
        except (imaplib.IMAP4.error, socket.timeout, OSError, Exception) as exc:
            logger.error("IMAP connection failed: %s", exc)
            return 0

        processed_count = 0
        try:
            _, data = imap.search(None, "UNSEEN")
            uid_list = data[0].split() if data and data[0] else []

            for uid_bytes in uid_list:
                uid = uid_bytes.decode()
                if self._uid_already_processed(uid):
                    continue

                message = self._fetch_message(imap, uid)
                if message is None:
                    continue

                classification = self.classify_reply(message)
                try:
                    self._dispatch(message, classification)
                    self._mark_uid_processed(uid)
                    processed_count += 1
                except Exception as exc:
                    # Do NOT store UID — allow retry on next poll.
                    logger.error(
                        "Downstream action failed for UID %s (%s): %s",
                        uid,
                        classification,
                        exc,
                    )
        finally:
            try:
                imap.close()
                imap.logout()
            except Exception:
                pass

        return processed_count

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def classify_reply(self, message: EmailMessage) -> ReplyClassification:
        """
        Classify an email as one of: interested / not_interested / auto_reply / bounce.

        Tries Ollama first; falls back to deterministic heuristics if Ollama
        is unavailable.
        """
        try:
            label = self._classify_with_ollama(message)
            if label in {"interested", "not_interested", "auto_reply", "bounce"}:
                return label  # type: ignore[return-value]
        except Exception as exc:
            logger.warning("Ollama unavailable for classification: %s — using heuristics.", exc)

        return self._classify_with_heuristics(message)

    def _classify_with_ollama(self, message: EmailMessage) -> str:
        """Call local Ollama to classify the reply."""
        import requests

        ollama_base = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
        prompt = (
            "Classify this email reply as exactly one of: interested, not_interested, "
            "auto_reply, bounce. Respond with only the label.\n\n"
            f"From: {message.sender}\n"
            f"Subject: {message.subject}\n"
            f"Body:\n{message.body[:10000]}"
        )
        resp = requests.post(
            f"{ollama_base}/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=self._ollama_timeout,
        )
        resp.raise_for_status()
        raw: str = resp.json().get("response", "").strip().lower()
        for label in ("interested", "not_interested", "auto_reply", "bounce"):
            if label in raw:
                return label
        return "interested"  # safe default when response is ambiguous

    def _classify_with_heuristics(self, message: EmailMessage) -> ReplyClassification:
        """
        Deterministic heuristic rules applied in order:
        1. Bounce — Return-Path is <> OR subject matches bounce pattern.
        2. Auto-reply — body contains out-of-office / vacation keywords.
        3. Not-interested — body contains unsubscribe / remove-me keywords.
        4. Default → interested.
        """
        # Rule 1: Bounce
        if message.return_path.strip() in ("<>", "") or _BOUNCE_SUBJECT_RE.search(
            message.subject
        ):
            return "bounce"

        # Rule 2: Auto-reply
        if _AUTO_REPLY_BODY_RE.search(message.body):
            return "auto_reply"

        # Rule 3: Not interested
        if _UNSUBSCRIBE_BODY_RE.search(message.body):
            return "not_interested"

        return "interested"

    # ------------------------------------------------------------------
    # Downstream actions
    # ------------------------------------------------------------------

    def _dispatch(self, message: EmailMessage, classification: ReplyClassification) -> None:
        """Route classified reply to the appropriate downstream handler."""
        from backend.db.models import Lead
        from backend.db.models_outreach import SequenceEnrollment

        db = self._get_db()
        lead = db.query(Lead).filter(Lead.email == message.sender).first()

        if lead is None:
            # Unmatched sender — log and continue.
            logger.info(
                "Reply from unmatched sender %s (UID %s) — no lead record found.",
                message.sender,
                message.uid,
            )
            return

        enrollment = (
            db.query(SequenceEnrollment)
            .filter(
                SequenceEnrollment.lead_id == lead.id,
                SequenceEnrollment.status.in_(["active", "paused"]),
            )
            .first()
        )

        if classification == "interested":
            self._handle_interested(db, lead, enrollment, message)
        elif classification == "not_interested":
            self._handle_not_interested(db, lead, enrollment)
        elif classification == "auto_reply":
            self._handle_auto_reply(db, enrollment)
        elif classification == "bounce":
            self._handle_bounce(db, lead, enrollment, message)

    def _handle_interested(self, db, lead, enrollment, message: EmailMessage) -> None:
        from backend.services.event_bus import event_bus

        if enrollment:
            enrollment.status = "replied_interested"

        # Create high-priority ticket
        try:
            from backend.services.ticket_service import TicketService

            ts = TicketService(db)
            ts.create_ticket(
                title=f"Interested reply from {message.sender}",
                instruction=message.body[:1000],
                priority="high",
                tags="outreach,interested",
            )
        except Exception as exc:
            logger.warning("Could not create ticket for interested reply: %s", exc)

        db.commit()

        event_bus.publish(
            "reply_classified",
            {"lead_id": lead.id, "classification": "interested"},
        )
        event_bus.publish(
            "reply_received",
            {"lead_id": lead.id, "classification": "interested"},
        )

    def _handle_not_interested(self, db, lead, enrollment) -> None:
        from backend.services.event_bus import event_bus

        if enrollment:
            enrollment.status = "replied_uninterested"
            db.commit()
        event_bus.publish(
            "reply_received",
            {"lead_id": lead.id, "classification": "not_interested"},
        )

    def _handle_auto_reply(self, db, enrollment) -> None:
        if enrollment:
            enrollment.status = "paused"
            db.commit()

    def _handle_bounce(self, db, lead, enrollment, message: EmailMessage) -> None:
        from backend.db.models_outreach import ProcessedEmailUID

        lead.email_invalid = True
        if enrollment:
            enrollment.status = "failed"

        # Write bounce event record
        evt = ProcessedEmailUID(
            id=str(uuid.uuid4()),
            mailbox=self._mailbox,
            uid=f"bounce_{message.uid}",
        )
        db.add(evt)
        db.commit()

    # ------------------------------------------------------------------
    # IMAP helpers
    # ------------------------------------------------------------------

    def _fetch_message(self, imap: imaplib.IMAP4_SSL, uid: str) -> "EmailMessage | None":
        """Fetch and parse a single message by UID."""
        import email as email_lib

        try:
            _, msg_data = imap.fetch(uid, "(RFC822)")
            if not msg_data or not msg_data[0]:
                return None
            raw = msg_data[0][1]
            if isinstance(raw, bytes):
                msg = email_lib.message_from_bytes(raw)
            else:
                msg = email_lib.message_from_string(str(raw))

            sender = msg.get("From", "")
            subject = msg.get("Subject", "")
            return_path = msg.get("Return-Path", "")

            body_parts: list[str] = []
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_parts.append(payload.decode(errors="replace")[:10000])
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body_parts.append(payload.decode(errors="replace")[:10000])

            body = " ".join(body_parts)[:10000]

            # Extract bare email from "Name <email>" format
            bare_sender_match = re.search(r"<([^>]+)>", sender)
            if bare_sender_match:
                sender = bare_sender_match.group(1).strip()

            return EmailMessage(
                uid=uid,
                sender=sender.strip(),
                subject=subject.strip(),
                body=body,
                return_path=return_path,
            )
        except Exception as exc:
            logger.error("Failed to parse message UID %s: %s", uid, exc)
            return None

    # ------------------------------------------------------------------
    # UID dedup helpers
    # ------------------------------------------------------------------

    def _uid_already_processed(self, uid: str) -> bool:
        from backend.db.models_outreach import ProcessedEmailUID

        db = self._get_db()
        try:
            existing = (
                db.query(ProcessedEmailUID)
                .filter(
                    ProcessedEmailUID.mailbox == self._mailbox,
                    ProcessedEmailUID.uid == uid,
                )
                .first()
            )
            return existing is not None
        finally:
            self._maybe_close(db)

    def _mark_uid_processed(self, uid: str) -> None:
        from backend.db.models_outreach import ProcessedEmailUID

        db = self._get_db()
        try:
            record = ProcessedEmailUID(
                id=str(uuid.uuid4()),
                mailbox=self._mailbox,
                uid=uid,
            )
            db.add(record)
            db.commit()
        finally:
            self._maybe_close(db)

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _get_db(self):
        if self._db is not None:
            return self._db
        from backend.db.session import SessionLocal

        return SessionLocal()

    def _maybe_close(self, db) -> None:
        if self._db is None:
            db.close()
