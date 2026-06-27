"""  # noqa: E501
Workflows API — create, inspect, and control multi-step workflows.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.db.models import Workflow
from backend.services.workflow_service import WorkflowService
from backend.auth.middleware import get_current_active_user

router = APIRouter(prefix="/api/workflows", tags=["Workflows"])


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────


class StepDefinition(BaseModel):
    step_name: str
    step_type: str  # ticket/notification/approval/condition
    input: Optional[dict] = None


class WorkflowCreate(BaseModel):
    name: str
    steps: List[StepDefinition]
    company_id: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    body: WorkflowCreate,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new workflow definition."""
    svc = WorkflowService(db)
    wf = svc.create_workflow(
        name=body.name,
        steps=[s.model_dump() for s in body.steps],
        company_id=body.company_id,
    )
    return svc.get_status(wf.id)


@router.get("")
async def list_workflows(
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all workflows (most recent first)."""
    limit = min(max(limit, 1), 200)
    rows = db.query(Workflow).order_by(Workflow.created_at.desc()).offset(skip).limit(limit).all()
    svc = WorkflowService(db)
    return {
        "skip": skip,
        "limit": limit,
        "items": [svc.get_status(w.id) for w in rows],
    }


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get the current status and step details of a workflow."""
    svc = WorkflowService(db)
    result = svc.get_status(workflow_id)
    if not result:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return result


@router.post("/{workflow_id}/start")
async def start_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Start a pending workflow."""
    svc = WorkflowService(db)
    wf = svc.start_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return svc.get_status(workflow_id)


@router.post("/{workflow_id}/pause")
async def pause_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Pause a running workflow."""
    svc = WorkflowService(db)
    wf = svc.pause_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return svc.get_status(workflow_id)


@router.post("/{workflow_id}/resume")
async def resume_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Resume a paused workflow."""
    svc = WorkflowService(db)
    wf = svc.resume_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return svc.get_status(workflow_id)


@router.post("/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Cancel a workflow (marks as failed)."""
    svc = WorkflowService(db)
    wf = svc.cancel_workflow(workflow_id, user_id=current_user["id"])
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return svc.get_status(workflow_id)
