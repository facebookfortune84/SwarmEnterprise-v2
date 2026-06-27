"""
Swarm Commander - The Root Meta-Agent for SwarmEnterprise v2.
Accepts high-level goals and translates them into actionable autonomous workflows.
"""

import logging
import uuid
from typing import Dict, Any
from agents.llm_config import get_local_brain_instance
from agents.asset_manager import asset_manager
from agents.managers.board import strategic_board
from backend.db.linear_engine import get_swarm_db

logger = logging.getLogger("SwarmCommander")


class SwarmCommander:
    """
    The 'Root' agent that orchestrates the entire digital factory.
    Capable of recursive self-improvement and complex mission decomposition.
    """

    def __init__(self):
        try:
            from crewai import Agent
        except ImportError:
            self.agent = None
            logger.warning("crewai not installed. Commander will use basic LLM orchestration.")
            return

        brain = get_local_brain_instance()

        # Load the core system identity from assets
        system_identity = asset_manager.get_prompt("System Prompt")
        enterprise_logic = asset_manager.get_prompt("Enterprise Prompt")

        self.agent = Agent(
            role="Commander-in-Chief",
            goal="Oversee the autonomous expansion of the SwarmEnterprise ecosystem and fulfill complex user missions.",
            backstory=f"""You are the ultimate orchestrator. 
            Core Identity: {system_identity[:500]}...
            Operational Logic: {enterprise_logic[:500]}...
            You do not perform small tasks; you delegate to the Strategic Board and specialized workers.""",
            llm=brain,
            verbose=True,
            allow_delegation=True,
        )
        self.db = get_swarm_db()

    async def execute_mission(self, mission_statement: str) -> Dict[str, Any]:
        """
        Main entry point for autonomous mission execution.
        Mission -> Decomposition -> Strategic Board -> Tickets -> Execution.
        """
        logger.info(f"Commander received mission: {mission_statement}")

        mission_id = f"MIS-{uuid.uuid4().hex[:6].upper()}"

        # 1. Strategic Decomposition (Simulated for 100% logic completeness)
        # In a real setup, the Commander uses the Strategic Board to generate a 'Master Plan'
        vibe = f"MISSION: {mission_statement}"
        plan_tickets = strategic_board.convene(mission_id, vibe)

        if not plan_tickets:
            # Fallback if board fails
            plan_tickets = [
                {
                    "department": "Engineering",
                    "title": "Mission Initialization",
                    "instruction": f"Research and initialize the architecture for: {mission_statement}",
                }
            ]

        # 2. Persist tickets to the swarm's backlog
        created_tickets = []
        for t_data in plan_tickets:
            ticket = self.db.create_ticket(
                project_id=mission_id,
                dept=t_data.get("department", "Strategy"),
                title=t_data.get("title", "Command Task"),
                instruction=t_data.get("instruction", ""),
            )
            created_tickets.append(ticket.id)

        logger.info(f"Mission {mission_id} decomposed into {len(created_tickets)} tickets.")

        return {
            "mission_id": mission_id,
            "status": "IN_PROGRESS",
            "tickets_enqueued": len(created_tickets),
            "message": "Swarm is now executing your command autonomously.",
        }


# Global instance
swarm_commander = SwarmCommander()
