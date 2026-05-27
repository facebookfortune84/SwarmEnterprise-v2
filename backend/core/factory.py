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
        try:
            for task in plan:
                t = Ticket(
                    project_id=project_id,
                    department=task.get("department", "Engineering"),
                    title=task.get("title", "Task"),
                    instruction=task.get("instruction", ""),
                )
                db.add(t)
            db.commit()
            logger.info(f"FACTORY: {len(plan)} tickets created. Dispatching workers...")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save tickets: {e}")
            raise
        finally:
            db.close()

        # In the full loop, we would trigger execution_unit here for each ticket.

        return {"status": "success", "tickets_generated": len(plan)}


swarm_factory = SwarmFactory()
