"""
Tickets API — full CRUD + lifecycle endpoints.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.db.models import Ticket, TicketComment
from backend.db.ticket_history import get_history
from backend.services.ticket_service import TicketService
from backend.services.notification_service import NotificationService
from backend.auth.middleware import get_current_active_user, get_current_admin_user
from backend.services.event_bus import event_bus

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────


class TicketCreate(BaseModel):
    title: str
    instruction: str
    project_id: Optional[str] = None
    department: Optional[str] = None
    priority: Optional[str] = "medium"
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    sla_hours: Optional[int] = 24
    tags: Optional[str] = None
    parent_ticket_id: Optional[str] = None
    estimated_hours: Optional[float] = None


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    instruction: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    sla_hours: Optional[int] = None
    tags: Optional[str] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    status: Optional[str] = None


class AssignRequest(BaseModel):
    assignee_id: str


class CommentRequest(BaseModel):
    content: str


class ResolveRequest(BaseModel):
    actual_hours: Optional[float] = None


# ─────────────────────────────────────────────────────────────────────────────
# Serializer
# ─────────────────────────────────────────────────────────────────────────────


def _serialize_ticket(t: Ticket) -> dict:
    return {
        "id": t.id,
        "project_id": t.project_id,
        "department": t.department,
        "title": t.title,
        "instruction": t.instruction,
        "status": t.status,
        "priority": t.priority,
        "assignee_id": t.assignee_id,
        "reporter_id": t.reporter_id,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
        "sla_hours": t.sla_hours,
        "tags": t.tags,
        "parent_ticket_id": t.parent_ticket_id,
        "estimated_hours": t.estimated_hours,
        "actual_hours": t.actual_hours,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _serialize_comment(c: TicketComment) -> dict:
    return {
        "id": c.id,
        "ticket_id": c.ticket_id,
        "user_id": c.user_id,
        "content": c.content,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────


@router.get("")
async def list_tickets(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assignee_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List tickets with optional filters."""
    svc = TicketService(db)
    tickets = svc.list_tickets(
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return {
        "items": [_serialize_ticket(t) for t in tickets],
        "total": len(tickets),
        "skip": skip,
        "limit": limit,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_ticket(
    body: TicketCreate,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new ticket."""
    svc = TicketService(db)
    ticket = svc.create_ticket(
        title=body.title,
        instruction=body.instruction,
        project_id=body.project_id,
        department=body.department,
        priority=body.priority,
        assignee_id=body.assignee_id,
        reporter_id=current_user["id"],
        due_date=body.due_date,
        sla_hours=body.sla_hours,
        tags=body.tags,
        parent_ticket_id=body.parent_ticket_id,
        estimated_hours=body.estimated_hours,
    )
    # Notify assignee and publish event
    ns = NotificationService(db)
    ns.notify_ticket_created(ticket)
    event_bus.publish("ticket.created", {"ticket": ticket})
    return _serialize_ticket(ticket)


@router.get("/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve a ticket by ID."""
    svc = TicketService(db)
    ticket = svc.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _serialize_ticket(ticket)


@router.put("/{ticket_id}")
async def update_ticket(
    ticket_id: str,
    body: TicketUpdate,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update ticket fields."""
    svc = TicketService(db)
    fields = body.dict(exclude_unset=True, exclude_none=True)
    ticket = svc.update_ticket(ticket_id, user_id=current_user["id"], **fields)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _serialize_ticket(ticket)


@router.delete("/{ticket_id}", status_code=status.HTTP_200_OK)
async def delete_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Delete a ticket (admin only)."""
    svc = TicketService(db)
    if not svc.delete_ticket(ticket_id):
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"ok": True}


@router.post("/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: str,
    body: AssignRequest,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Assign a ticket to a user."""
    svc = TicketService(db)
    ticket = svc.assign(ticket_id, assignee_id=body.assignee_id, user_id=current_user["id"])
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ns = NotificationService(db)
    ns.notify_ticket_created(ticket)
    return _serialize_ticket(ticket)


@router.post("/{ticket_id}/escalate")
async def escalate_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Escalate ticket priority by one level."""
    svc = TicketService(db)
    ticket = svc.escalate(ticket_id, user_id=current_user["id"])
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    event_bus.publish("ticket.escalated", {"ticket": ticket})
    return _serialize_ticket(ticket)


@router.post("/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: str,
    body: ResolveRequest,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Mark a ticket as resolved."""
    svc = TicketService(db)
    ticket = svc.resolve(ticket_id, user_id=current_user["id"], actual_hours=body.actual_hours)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _serialize_ticket(ticket)


@router.post("/{ticket_id}/close")
async def close_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Close a resolved ticket."""
    svc = TicketService(db)
    ticket = svc.close(ticket_id, user_id=current_user["id"])
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _serialize_ticket(ticket)


@router.post("/{ticket_id}/comment", status_code=status.HTTP_201_CREATED)
async def add_comment(
    ticket_id: str,
    body: CommentRequest,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Add a comment to a ticket."""
    svc = TicketService(db)
    if not svc.get_ticket(ticket_id):
        raise HTTPException(status_code=404, detail="Ticket not found")
    comment = svc.add_comment(ticket_id, user_id=current_user["id"], content=body.content)
    return _serialize_comment(comment)


@router.get("/{ticket_id}/history")
async def get_ticket_history(
    ticket_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Return the full audit trail for a ticket."""
    svc = TicketService(db)
    if not svc.get_ticket(ticket_id):
        raise HTTPException(status_code=404, detail="Ticket not found")
    return get_history(db, ticket_id)
