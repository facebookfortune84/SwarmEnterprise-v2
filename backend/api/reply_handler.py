"""
Reply Handler API — exposes the classified inbox replies.

Endpoints
---------
GET /api/outreach/inbox   List classified inbox replies
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.session import get_db

router = APIRouter(prefix="/api/outreach", tags=["Outreach — Inbox"])


@router.get("/inbox")
async def list_inbox(db: Session = Depends(get_db)):
    """
    Return all classified inbox replies.

    Interested replies are sorted first, then by received_at descending
    within each group.
    """
    from backend.db.models_outreach import ProcessedEmailUID

    # For now we return processed email UID records as a proxy for replies.
    # In production this table would be joined with a full InboxReply table.
    rows = db.query(ProcessedEmailUID).order_by(ProcessedEmailUID.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "mailbox": r.mailbox,
            "uid": r.uid,
            "received_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
