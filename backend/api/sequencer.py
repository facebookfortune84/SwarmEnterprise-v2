"""
Sequencer API — CRUD for outreach sequences and enrolment management.

Endpoints
---------
POST   /api/outreach/sequence         Create a sequence
GET    /api/outreach/sequences        List all sequences with counts
POST   /api/outreach/sequence/enroll  Enrol leads in a sequence
"""

from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.session import get_db

router = APIRouter(prefix="/api/outreach", tags=["Outreach — Sequences"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class SequenceStepSchema(BaseModel):
    delay_days: int = Field(..., ge=0, le=365)
    subject_template: str = Field(..., min_length=1, max_length=998)
    body_template: str = Field(..., min_length=1, max_length=100_000)


class CreateSequenceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    steps: List[SequenceStepSchema] = Field(..., min_length=1, max_length=10)
    status: str = Field(default="active", pattern="^(active|paused|archived)$")


class EnrollRequest(BaseModel):
    lead_ids: List[str] = Field(..., min_length=1)
    sequence_id: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/sequence", status_code=201)
async def create_sequence(payload: CreateSequenceRequest, db: Session = Depends(get_db)):
    """Create a new outreach email sequence."""
    from agents.outreach.sequencer_agent import SequencerAgent

    agent = SequencerAgent(db_session=db)
    try:
        seq = agent.create_sequence(
            {
                "name": payload.name,
                "steps": [s.model_dump() for s in payload.steps],
                "status": payload.status,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {
        "id": seq.id,
        "name": seq.name,
        "status": seq.status,
        "step_count": len(payload.steps),
        "created_at": seq.created_at.isoformat() if seq.created_at else None,
    }


@router.get("/sequences")
async def list_sequences(db: Session = Depends(get_db)):
    """List all sequences with step count and enrolled prospect count."""
    from backend.db.models_outreach import Sequence, SequenceEnrollment

    sequences = db.query(Sequence).all()
    result = []
    for seq in sequences:
        enrolled = (
            db.query(SequenceEnrollment)
            .filter(SequenceEnrollment.sequence_id == seq.id)
            .count()
        )
        steps = json.loads(seq.steps_json or "[]")
        result.append(
            {
                "id": seq.id,
                "name": seq.name,
                "status": seq.status,
                "step_count": len(steps),
                "enrolled_count": enrolled,
                "created_at": seq.created_at.isoformat() if seq.created_at else None,
            }
        )
    return result


@router.post("/sequence/enroll")
async def enroll_leads(payload: EnrollRequest, db: Session = Depends(get_db)):
    """Enrol one or more leads in a sequence."""
    from agents.outreach.sequencer_agent import SequencerAgent
    from backend.db.models_outreach import Sequence

    seq = db.query(Sequence).filter(Sequence.id == payload.sequence_id).first()
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found.")

    agent = SequencerAgent(db_session=db)
    enrolled = []
    conflicts = []

    for lead_id in payload.lead_ids:
        try:
            enrollment = agent.enroll_prospect(lead_id, payload.sequence_id)
            enrolled.append({"lead_id": lead_id, "enrollment_id": enrollment.id})
        except ValueError as exc:
            conflicts.append({"lead_id": lead_id, "reason": str(exc)})

    if conflicts and not enrolled:
        raise HTTPException(
            status_code=409,
            detail={"message": "All enrollments conflict.", "conflicts": conflicts},
        )

    return {
        "enrolled": enrolled,
        "conflicts": conflicts,
        "enrolled_count": len(enrolled),
    }
