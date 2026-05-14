from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.db.linear_engine import get_swarm_db

router = APIRouter(prefix="/api/usage", tags=["Usage"])

class UsageRecord(BaseModel):
    project_id: str | None = None
    event_type: str
    amount: str | None = None
    metadata: dict | None = None

@router.post("/record")
async def record_usage(payload: UsageRecord):
    db = get_swarm_db()
    uid = db.record_usage(payload.project_id, payload.event_type, payload.amount, payload.metadata)
    return {"usage_id": uid}

@router.get("/list")
async def list_usage(project_id: str | None = None, limit: int = 100):
    db = get_swarm_db()
    rows = db.list_usage(project_id=project_id, limit=limit)
    return {"usage": rows}
