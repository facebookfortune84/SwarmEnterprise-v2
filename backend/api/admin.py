from fastapi import APIRouter, HTTPException
from backend.db.linear_engine import get_swarm_db

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/projects")
async def list_projects(limit: int = 100):
    db = get_swarm_db()
    projects = db.list_projects(limit=limit)
    return {"projects": projects}

@router.get("/project/{project_id}")
async def get_project(project_id: str):
    db = get_swarm_db()
    p = db.get_project(project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return p
