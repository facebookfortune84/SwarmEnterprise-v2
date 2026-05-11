import logging
from agents.managers.board import strategic_board
from backend.db.linear_engine import swarm_db

logger = logging.getLogger("SwarmFactory")

class SwarmFactory:
    """Coordinates the transition from Directives to Physical Code."""
    
    def run_production_cycle(self, project_id: str, description: str):
        logger.info(f"FACTORY: Convening Board for {project_id}...")
        
        # 1. Board Strategy Phase
        plan = strategic_board.convene(project_id, description)
        
        # 2. Save Tickets to Database
        for task in plan:
            swarm_db.create_ticket(
                project_id=project_id,
                dept=task.get('department', 'Engineering'),
                title=task.get('title', 'Task'),
                instruction=task.get('instruction', '')
            )
            
        logger.info(f"FACTORY: {len(plan)} tickets created. Dispatching workers...")
        # In the full loop, we would trigger execution_unit here for each ticket.
        
        return {"status": "success", "tickets_generated": len(plan)}

swarm_factory = SwarmFactory()
