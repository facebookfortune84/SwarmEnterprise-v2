"""
Admin API routes for managing and inspecting projects.

This module exposes administrative endpoints for listing projects
and retrieving individual project details from the swarm database.
"""

from fastapi import APIRouter, HTTPException
from backend.db.linear_engine import get_swarm_db

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/projects")
async def list_projects(limit: int = 100):
    """
    Return a list of projects stored in the swarm database.

    Args:
        limit (int): Maximum number of projects to return.

    Returns:
        dict: A dictionary containing a list of project records.
    """
    db = get_swarm_db()
    projects = db.list_projects(limit=limit)
    return {"projects": projects}


@router.get("/project/{project_id}")
async def get_project(project_id: str):
    """
    Retrieve a single project by its unique identifier.

    Args:
        project_id (str): The ID of the project to retrieve.

    Raises:
        HTTPException: If the project does not exist.

    Returns:
        dict: The project record.
    """
    db = get_swarm_db()
    project = db.get_project(project_id)

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return project
