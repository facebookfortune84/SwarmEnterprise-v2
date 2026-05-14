from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.db.linear_engine import get_swarm_db

router = APIRouter(prefix="/api/leads", tags=["Leads"])

class LeadCreate(BaseModel):
    email: str
    name: str | None = None
    company: str | None = None
    metadata: dict | None = None

@router.post("/")
async def create_lead(payload: LeadCreate):
    db = get_swarm_db()
    lead_id = db.create_lead(payload.email, name=payload.name, company=payload.company, metadata=payload.metadata)
    return {"lead_id": lead_id}

@router.get("/")
async def list_leads(limit: int = 100):
    db = get_swarm_db()
    leads = db.list_leads(limit=limit)
    return {"leads": leads}

@router.get("/{lead_id}")
async def get_lead(lead_id: str):
    db = get_swarm_db()
    l = db.get_lead(lead_id)
    if not l:
        raise HTTPException(status_code=404, detail="Lead not found")
    return l

@router.post("/{lead_id}/ticket")
async def create_ticket_for_lead(lead_id: str, department: str = "sales", title: str = "Follow-up", instruction: str = "Contact lead"):
    db = get_swarm_db()
    lead = db.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.create_ticket(lead.get('id'), department, title, instruction)
    return {"status": "ticket_created"}
