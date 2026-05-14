from fastapi import APIRouter
from pydantic import BaseModel
from agents.outreach.worker import enqueue_outreach

router = APIRouter(prefix="/api/outreach", tags=["Outreach"])

class OutreachPayload(BaseModel):
    email: str
    subject: str
    body: str

@router.post("/")
async def send_outreach(payload: OutreachPayload):
    """Enqueue an outreach email to be sent by the outreach worker.
    This is best-effort and returns immediately after queuing.
    """
    enqueue_outreach(payload.email, payload.subject, payload.body)
    return {"status": "enqueued"}
