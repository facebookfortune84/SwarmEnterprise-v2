"""
Reporting API — daily outreach metrics.

Endpoints
---------
GET /api/outreach/reports/daily   Fetch daily metric snapshots for a date range
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db.session import get_db

router = APIRouter(prefix="/api/outreach", tags=["Outreach — Reports"])


@router.get("/reports/daily")
async def get_daily_reports(
    start_date: str = Query(..., description="ISO 8601 date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="ISO 8601 date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    Return daily outreach metric snapshots for the requested date range.

    Returns HTTP 400 if parameters are missing, malformed, or start > end.
    Returns HTTP 200 with empty array if no data exists.
    """
    try:
        start = date.fromisoformat(start_date)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail={"error": f"Invalid start_date '{start_date}'. Use ISO 8601 format YYYY-MM-DD."},
        )
    try:
        end = date.fromisoformat(end_date)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail={"error": f"Invalid end_date '{end_date}'. Use ISO 8601 format YYYY-MM-DD."},
        )
    if start > end:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"start_date ({start_date}) must not be after end_date ({end_date})."
            },
        )

    from agents.outreach.reporting_agent import ReportingAgent

    agent = ReportingAgent(db_session=db)
    return agent.get_metrics_range(start, end)
