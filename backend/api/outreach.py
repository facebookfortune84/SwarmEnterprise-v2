"""
Outreach API endpoints.

This module exposes a simple endpoint for enqueueing outbound outreach
tasks such as sending emails. The actual processing is handled by the
outreach worker system.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from agents.outreach.worker import enqueue_outreach

router = APIRouter(prefix="/api/outreach", tags=["Outreach"])


class OutreachPayload(BaseModel):
    """Payload for initiating an outreach action."""

    email: str
    subject: str
    body: str


@router.post("/")
async def send_outreach(payload: OutreachPayload):
    """
    Enqueue an outreach task for asynchronous processing.

    Args:
        payload (OutreachPayload): Email, subject, and body content.

    Returns:
        dict: Status of the enqueue operation.
    """
    enqueue_outreach(
        to_email=payload.email,
        subject=payload.subject,
        body=payload.body,
    )
    return {"status": "queued"}
