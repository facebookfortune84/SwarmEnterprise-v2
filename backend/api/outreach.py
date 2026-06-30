"""
Outreach API endpoints.

This module exposes endpoints for enqueueing outbound outreach tasks and
campaign-style email blasts. The actual processing is handled by the
outreach worker system.
"""

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from agents.outreach.worker import enqueue_campaign, enqueue_outreach

router = APIRouter(prefix="/api/outreach", tags=["Outreach"])


class OutreachPayload(BaseModel):
    """Payload for initiating a single outreach action."""

    email: str = Field(..., description="Recipient email address")
    subject: str = Field(..., min_length=1, description="Email subject")
    body: str = Field(..., min_length=1, description="Email body")


class CampaignPayload(BaseModel):
    """Payload for initiating a multi-recipient outreach campaign."""

    recipients: List[str] = Field(..., min_length=1, description="Recipient email addresses")
    subject: str = Field(..., min_length=1, description="Campaign subject")
    body: str = Field(..., min_length=1, description="Campaign body")
    from_name: str = Field(default="SwarmOS", description="Display name for the sender")


@router.post("/")
async def send_outreach(payload: OutreachPayload):
    """Enqueue a single outbound outreach task for asynchronous processing."""
    enqueue_outreach(
        to_email=payload.email,
        subject=payload.subject,
        body=payload.body,
    )
    return {"status": "queued", "queued": 1}


@router.post("/campaign")
async def send_campaign(payload: CampaignPayload):
    """Enqueue a multi-recipient outreach campaign for asynchronous processing."""
    enqueue_campaign(
        recipients=payload.recipients,
        subject=payload.subject,
        body=payload.body,
        from_name=payload.from_name,
    )
    return {
        "status": "queued",
        "queued": len(payload.recipients),
        "recipients": payload.recipients,
    }
