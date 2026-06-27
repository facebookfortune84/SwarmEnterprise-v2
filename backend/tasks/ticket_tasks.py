"""
Ticket-related Celery tasks.
"""
import logging
from backend.celery_app import celery_app

logger = logging.getLogger("tasks.tickets")


@celery_app.task(
    name="backend.tasks.ticket_tasks.process_ticket",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_ticket(self, ticket_id: str):
    """
    Execute a ticket through the agent system.

    Loads the ticket from the database, dispatches it to the appropriate
    department agent, and updates status on completion or failure.

    Args:
        ticket_id: The ID of the ticket to process.
    """
    from backend.db.session import SessionLocal
    from backend.services.ticket_service import TicketService
    from backend.services.event_bus import event_bus

    db = SessionLocal()
    try:
        svc = TicketService(db)
        ticket = svc.get_ticket(ticket_id)
        if not ticket:
            logger.warning("process_ticket: ticket %s not found", ticket_id)
            return {"error": "ticket_not_found", "ticket_id": ticket_id}

        svc.update_ticket(ticket_id, user_id=None, status="IN_PROGRESS")

        # Delegate to the department agent if available
        try:
            from backend.core.factory import swarm_factory

            result = swarm_factory.run_production_cycle(
                project_id=ticket.project_id or ticket_id,
                description=ticket.instruction or ticket.title,
            )
        except Exception as agent_exc:
            logger.exception("Agent execution failed for ticket %s", ticket_id)
            svc.update_ticket(ticket_id, user_id=None, status="OPEN")
            event_bus.publish("task.failed", {"task_id": ticket_id, "error": str(agent_exc)})
            raise self.retry(exc=agent_exc)

        svc.resolve(ticket_id, user_id=None)
        event_bus.publish("task.completed", {"task_id": ticket_id, "result": str(result)})
        logger.info("process_ticket: ticket %s resolved", ticket_id)
        return {"ok": True, "ticket_id": ticket_id}
    finally:
        db.close()


@celery_app.task(name="backend.tasks.ticket_tasks.check_sla_breaches")
def check_sla_breaches():
    """
    Periodic task — scan all open tickets for SLA violations.
    Delegates to TicketService.check_sla_breaches() which escalates
    and notifies admins automatically.
    """
    from backend.db.session import SessionLocal
    from backend.services.ticket_service import TicketService

    db = SessionLocal()
    try:
        svc = TicketService(db)
        breached = svc.check_sla_breaches()
        logger.info("check_sla_breaches: %d ticket(s) breached", len(breached))
        return {"breached": [t.id for t in breached]}
    finally:
        db.close()


@celery_app.task(name="backend.tasks.ticket_tasks.escalate_overdue_tickets")
def escalate_overdue_tickets():
    """
    Periodic task — escalate every ticket whose due_date has passed and is
    still open.  This supplements the SLA check with explicit due-date
    enforcement.
    """
    from datetime import datetime
    from backend.db.session import SessionLocal
    from backend.db.models import Ticket
    from backend.services.ticket_service import TicketService

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        overdue = (
            db.query(Ticket)
            .filter(
                Ticket.due_date != None,
                Ticket.due_date < now,
                Ticket.status.in_(["OPEN", "IN_PROGRESS"]),
            )
            .all()
        )
        svc = TicketService(db)
        escalated = []
        for ticket in overdue:
            svc.escalate(ticket.id, user_id=None)
            escalated.append(ticket.id)
        logger.info("escalate_overdue_tickets: %d escalated", len(escalated))
        return {"escalated": escalated}
    finally:
        db.close()
