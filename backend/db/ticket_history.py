"""
Ticket audit trail — record and retrieve every field change on a ticket.
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from backend.db.models import TicketHistory

logger = logging.getLogger("TicketHistory")


def record_change(
    db: Session,
    ticket_id: str,
    action: str,
    user_id: str = None,
    old_value: str = None,
    new_value: str = None,
) -> TicketHistory:
    """
    Persist one audit entry for a ticket mutation.

    Args:
        db: SQLAlchemy session.
        ticket_id: The ticket being changed.
        action: Short verb describing the change, e.g. 'status_changed'.
        user_id: Who triggered the change (None for system actions).
        old_value: String representation of the previous value.
        new_value: String representation of the new value.

    Returns:
        The persisted TicketHistory row.
    """
    entry = TicketHistory(
        ticket_id=ticket_id,
        user_id=user_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    logger.debug("Recorded ticket history: ticket=%s action=%s", ticket_id, action)
    return entry


def get_history(db: Session, ticket_id: str) -> list[dict]:
    """
    Return the full chronological audit trail for a ticket.

    Args:
        db: SQLAlchemy session.
        ticket_id: The ticket whose history is requested.

    Returns:
        List of history entries as dicts, oldest first.
    """
    rows = (
        db.query(TicketHistory)
        .filter(TicketHistory.ticket_id == ticket_id)
        .order_by(TicketHistory.created_at.asc())
        .all()
    )
    return [
        {
            "id": r.id,
            "ticket_id": r.ticket_id,
            "user_id": r.user_id,
            "action": r.action,
            "old_value": r.old_value,
            "new_value": r.new_value,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
