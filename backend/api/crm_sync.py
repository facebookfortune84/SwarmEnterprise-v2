"""
CRM Sync API — lead timeline endpoint.

Endpoints
---------
GET /api/leads/{lead_id}/timeline   Chronological status-transition log
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.session import get_db

router = APIRouter(prefix="/api/leads", tags=["Leads — Timeline"])


@router.get("/{lead_id}/timeline")
async def get_lead_timeline(lead_id: str, db: Session = Depends(get_db)):
    """
    Return a chronological array of status transitions for the given lead.

    Returns HTTP 404 if no lead with the given id exists.
    """
    from backend.db.models import Lead
    from backend.db.models_outreach import LeadTimeline

    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    entries = (
        db.query(LeadTimeline)
        .filter(LeadTimeline.lead_id == lead_id)
        .order_by(LeadTimeline.occurred_at.asc())
        .all()
    )

    return [
        {
            "from_status": e.from_status,
            "to_status": e.to_status,
            "triggered_by": e.triggered_by,
            "occurred_at": e.occurred_at.isoformat(),
        }
        for e in entries
    ]
