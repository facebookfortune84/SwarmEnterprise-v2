"""
Core engine API endpoints.

This module exposes the build trigger endpoint and background execution
wrapper for running SwarmFactory production cycles safely.
"""

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from backend.core.factory import swarm_factory

router = APIRouter(prefix="/api", tags=["Core Engine"])
logger = logging.getLogger("SwarmFactoryAPI")


def _safe_run_production_cycle(project_id: str, description: str):
    """
    Safely execute a production cycle in the background.

    This wrapper ensures that exceptions raised during background
    execution are logged without interrupting the main request flow.

    Args:
        project_id (str): The project identifier.
        description (str): Description of the build context.
    """
    try:
        swarm_factory.run_production_cycle(
            project_id=project_id,
            description=description,
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Background production cycle failed: %s", exc)


class BuildRequest(BaseModel):
    """Payload for triggering a new build."""

    name: str
    description: str
    stack: str


@router.post("/build")
async def trigger_build(request: BuildRequest, background_tasks: BackgroundTasks):
    """
    Trigger a new build and run the SwarmFactory production cycle in the background.

    Args:
        request (BuildRequest): Build metadata including name, description, and stack.
        background_tasks (BackgroundTasks): FastAPI background task manager.

    Raises:
        HTTPException: If an unexpected error occurs.

    Returns:
        dict: Status message and generated project ID.
    """
    try:
        project_id = f"PROJ-{uuid.uuid4().hex[:6].upper()}"

        background_tasks.add_task(
            _safe_run_production_cycle,
            project_id=project_id,
            description=f"Stack: {request.stack}. Vibe: {request.description}",
        )

        return {
            "status": "Build Initialized",
            "project_id": project_id,
        }

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to trigger build: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
