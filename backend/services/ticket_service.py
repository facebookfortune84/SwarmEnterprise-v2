"""
Ticket service — full CRUD, SLA checking, and metrics.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from backend.db.models import Ticket, TicketComment
from backend.db.ticket_history import record_change

logger = logging.getLogger("TicketService")

VALID_PRIORITIES = {"low", "medium", "high", "critical"}
VALID_STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"}
ESCALATION_MAP = {"low": "medium", "medium": "high", "high": "critical", "critical": "critical"}


class TicketService:
    """Business logic for tickets."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ #
    # CRUD                                                                 #
    # ------------------------------------------------------------------ #

    def create_ticket(
        self,
        title: str,
        instruction: str,
        project_id: str = None,
        department: str = None,
        priority: str = "medium",
        assignee_id: str = None,
        reporter_id: str = None,
        due_date: datetime = None,
        sla_hours: int = 24,
        tags: str = None,
        parent_ticket_id: str = None,
        estimated_hours: float = None,
    ) -> Ticket:
        ticket = Ticket(
            project_id=project_id,
            department=department,
            title=title,
            instruction=instruction,
            priority=priority if priority in VALID_PRIORITIES else "medium",
            assignee_id=assignee_id,
            reporter_id=reporter_id,
            due_date=due_date,
            sla_hours=sla_hours,
            tags=tags,
            parent_ticket_id=parent_ticket_id,
            estimated_hours=estimated_hours,
        )
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        record_change(self.db, ticket.id, "created", user_id=reporter_id, new_value=title)
        return ticket

    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        return self.db.query(Ticket).filter(Ticket.id == ticket_id).first()

    def list_tickets(
        self,
        status: str = None,
        priority: str = None,
        assignee_id: str = None,
        date_from: datetime = None,
        date_to: datetime = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Ticket]:
        q = self.db.query(Ticket)
        if status:
            q = q.filter(Ticket.status == status)
        if priority:
            q = q.filter(Ticket.priority == priority)
        if assignee_id:
            q = q.filter(Ticket.assignee_id == assignee_id)
        if date_from:
            q = q.filter(Ticket.created_at >= date_from)
        if date_to:
            q = q.filter(Ticket.created_at <= date_to)
        return q.order_by(Ticket.created_at.desc()).offset(skip).limit(limit).all()

    def update_ticket(self, ticket_id: str, user_id: str, **fields) -> Optional[Ticket]:
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return None
        for field, value in fields.items():
            if hasattr(ticket, field) and value is not None:
                old = str(getattr(ticket, field))
                setattr(ticket, field, value)
                record_change(
                    self.db,
                    ticket_id,
                    f"{field}_changed",
                    user_id=user_id,
                    old_value=old,
                    new_value=str(value),
                )
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def delete_ticket(self, ticket_id: str) -> bool:
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return False
        self.db.delete(ticket)
        self.db.commit()
        return True

    # ------------------------------------------------------------------ #
    # Lifecycle transitions                                                #
    # ------------------------------------------------------------------ #

    def assign(self, ticket_id: str, assignee_id: str, user_id: str) -> Optional[Ticket]:
        return self.update_ticket(ticket_id, user_id, assignee_id=assignee_id)

    def escalate(self, ticket_id: str, user_id: str) -> Optional[Ticket]:
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return None
        new_priority = ESCALATION_MAP.get(ticket.priority or "medium", "high")
        return self.update_ticket(ticket_id, user_id, priority=new_priority)

    def resolve(self, ticket_id: str, user_id: str, actual_hours: float = None) -> Optional[Ticket]:
        fields = {"status": "RESOLVED", "resolved_at": datetime.utcnow()}
        if actual_hours is not None:
            fields["actual_hours"] = actual_hours
        ticket = self.update_ticket(ticket_id, user_id, **fields)
        if ticket:
            # Fire event so notification service can react
            try:
                from backend.services.event_bus import event_bus

                event_bus.publish("ticket.resolved", {"ticket": ticket})
            except Exception:
                pass
        return ticket

    def close(self, ticket_id: str, user_id: str) -> Optional[Ticket]:
        return self.update_ticket(ticket_id, user_id, status="CLOSED")

    def add_comment(self, ticket_id: str, user_id: str, content: str) -> TicketComment:
        comment = TicketComment(
            ticket_id=ticket_id,
            user_id=user_id,
            content=content,
            created_at=datetime.utcnow(),
        )
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        record_change(self.db, ticket_id, "comment_added", user_id=user_id, new_value=content[:200])
        return comment

    def get_comments(self, ticket_id: str) -> list[TicketComment]:
        return (
            self.db.query(TicketComment)
            .filter(TicketComment.ticket_id == ticket_id)
            .order_by(TicketComment.created_at.asc())
            .all()
        )

    # ------------------------------------------------------------------ #
    # SLA                                                                  #
    # ------------------------------------------------------------------ #

    def check_sla_breaches(self) -> list[Ticket]:
        """
        Find all open tickets whose SLA deadline has passed.
        Escalates them, records history, and notifies admins.

        Returns:
            List of breached Ticket rows.
        """
        now = datetime.utcnow()
        open_tickets = (
            self.db.query(Ticket).filter(Ticket.status.in_(["OPEN", "IN_PROGRESS"])).all()
        )
        breached = []
        for ticket in open_tickets:
            sla_deadline = ticket.created_at + timedelta(hours=ticket.sla_hours or 24)
            if now > sla_deadline:
                breached.append(ticket)
                self.escalate(ticket.id, user_id=None)
                record_change(
                    self.db,
                    ticket.id,
                    "sla_breached",
                    old_value=ticket.priority,
                    new_value=ESCALATION_MAP.get(ticket.priority, "high"),
                )
                try:
                    from backend.services.notification_service import NotificationService

                    ns = NotificationService(self.db)
                    ns.notify_task_failed(
                        task_id=f"sla:{ticket.id}",
                        error=f"SLA breached for ticket {ticket.id} ('{ticket.title}')",
                    )
                except Exception:
                    pass
        logger.info("SLA check: %d breached ticket(s)", len(breached))
        return breached

    # ------------------------------------------------------------------ #
    # Metrics                                                              #
    # ------------------------------------------------------------------ #

    def get_metrics(self) -> dict:
        """
        Return aggregate ticket counts by status and priority.

        Returns:
            Dict with 'by_status', 'by_priority', and 'total'.
        """
        all_tickets = self.db.query(Ticket).all()
        by_status: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        for t in all_tickets:
            by_status[t.status] = by_status.get(t.status, 0) + 1
            by_priority[t.priority or "medium"] = by_priority.get(t.priority or "medium", 0) + 1
        return {
            "total": len(all_tickets),
            "by_status": by_status,
            "by_priority": by_priority,
        }
