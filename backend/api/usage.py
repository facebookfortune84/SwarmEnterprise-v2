"""
Usage tracking API endpoints.

This module provides a simple endpoint for recording usage events
associated with projects, such as billing, activity tracking, or
system-level analytics.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from backend.db.linear_engine import get_swarm_db

router = APIRouter(prefix="/api/usage", tags=["Usage"])


class UsageRecord(BaseModel):
    """Payload for recording a usage event."""

    project_id: str | None = None
    event_type: str
    amount: str | None = None
    metadata: dict | None = None


@router.post("/record")
async def record_usage(payload: UsageRecord):
    """
    Record a usage event in the database.

    Args:
        payload (UsageRecord): Usage event details including project ID,
            event type, amount, and metadata.

    Returns:
        dict: The ID of the recorded usage entry.
    """
    db = get_swarm_db()
    usage_id = db.record_usage(
        payload.project_id,
        payload.event_type,
        payload.amount,
        payload.metadata,
    )
    return {"usage_id": usage_id}
