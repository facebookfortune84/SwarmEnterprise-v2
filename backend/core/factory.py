import logging
from backend.db.session import SessionLocal
from backend.db.models import Ticket

logger = logging.getLogger("SwarmFactory")


class SwarmFactory:
    """Coordinates the transition from Directives to Physical Code."""

    def run_production_cycle(self, project_id: str, description: str):
        logger.info(f"FACTORY: Convening Board for {project_id}...")

        # 1. Board Strategy Phase (import lazily to avoid heavy imports at module import time)
        from agents.managers.board import strategic_board

        plan = strategic_board.convene(project_id, description)

        # 2. Save Tickets to Database
        db = SessionLocal()
        saved_tickets = []
        try:
            for task in plan:
                t = Ticket(
                    project_id=project_id,
                    department=task.get("department", "Engineering"),
                    title=task.get("title", "Task"),
                    instruction=task.get("instruction", ""),
                )
                db.add(t)
                saved_tickets.append(t)
            db.commit()
            # Refresh to get assigned IDs
            for t in saved_tickets:
                db.refresh(t)
            logger.info(f"FACTORY: {len(plan)} tickets created. Dispatching workers...")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save tickets: {e}")
            raise
        finally:
            db.close()

        # 3. Enqueue each ticket for async execution
        from backend.queue import enqueue_task

        enqueued = 0
        for ticket in saved_tickets:
            try:
                enqueue_task(
                    {
                        "type": "execute_ticket",
                        "ticket_id": ticket.id,
                        "project_id": project_id,
                        "department": ticket.department,
                        "title": ticket.title,
                        "instruction": ticket.instruction,
                    }
                )
                enqueued += 1
            except Exception as e:
                logger.error(f"Failed to enqueue ticket {ticket.id}: {e}")

        logger.info(f"FACTORY: {enqueued}/{len(saved_tickets)} tickets enqueued for execution.")
        return {"status": "success", "tickets_generated": len(plan), "tickets_enqueued": enqueued}


swarm_factory = SwarmFactory()
