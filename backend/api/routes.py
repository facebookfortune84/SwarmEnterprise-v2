from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uuid
from backend.core.factory import swarm_factory

router = APIRouter(prefix="/api", tags=["Core Engine"])


def _safe_run_production_cycle(project_id: str, description: str):
    """Wrapper to run production cycle safely in background tasks.
    Ensures exceptions are caught and logged so background failures do not
    fail request handling during tests or in-production."""
    try:
        swarm_factory.run_production_cycle(project_id=project_id, description=description)
    except Exception as e:
        import logging
        logging.getLogger("SwarmFactory").exception("Background production cycle failed: %s", e)

class BuildRequest(BaseModel):
    name: str
    description: str
    stack: str

@router.post("/build")
async def trigger_build(request: BuildRequest, background_tasks: BackgroundTasks):
    try:
        project_id = f"PROJ-{uuid.uuid4().hex[:6].upper()}"
        
        # Trigger the AI Swarm in the background (safe wrapper)
        background_tasks.add_task(
            _safe_run_production_cycle,
            project_id=project_id,
            description=f"Stack: {request.stack}. Vibe: {request.description}"
        )
        
        return {"status": "Build Initialized", "project_id": project_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
