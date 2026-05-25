import json
import logging
import re
from typing import List, Dict, Any

# crewai is imported lazily inside methods to avoid import-time dependency issues
from agents.llm_config import get_local_brain_instance, get_embedder_config

logger = logging.getLogger("SwarmBoard")


class StrategicBoard:
    """Level 1: 12-Manager Oracle-Backed Board"""

    def __init__(self):
        self.brain = None
        self.roles = [
            "CTO",
            "CPO",
            "Chief Architect",
            "Security Director",
            "DevOps Director",
            "QA Director",
            "UI/UX Director",
            "Marketing Director",
            "Outreach Director",
            "Replicator Lead",
            "Documentation Manager",
            "Compliance Manager",
        ]

    def _get_agents(self) -> List[Any]:
        # Lazy import to avoid requiring crewai at import time
        try:
            from crewai import Agent
        except ImportError:
            raise RuntimeError(
                "crewai package required to construct Agent objects. Install or mock for tests."
            )

        brain = self.brain or get_local_brain_instance()
        # Pull prompts and SOPs from Oracle assets to enrich agent backstory
        try:
            from agents.asset_manager import get_oracle_assets

            oracle = get_oracle_assets()
        except Exception:
            oracle = None

        agents = []
        for role in self.roles:
            prompt_snippet = None
            if oracle:
                ctx = oracle.build_agent_context(role)
                prompt_snippet = ctx.get("prompt")

            backstory = f"You are the {role} of a Sovereign Swarm. You operate using FOSS principles. You output JSON tickets."
            if prompt_snippet:
                # Append a short snippet of the canonical prompt to the backstory to bias agent behavior
                backstory = (
                    backstory
                    + "\n\nCanonical Prompt:\n"
                    + (
                        prompt_snippet[:800] + "..."
                        if len(prompt_snippet) > 800
                        else prompt_snippet
                    )
                )

            agents.append(
                Agent(
                    role=role,
                    goal=f"Decompose the project vibe into technical tickets from the perspective of a {role}.",
                    backstory=backstory,
                    llm=brain,
                    verbose=True,
                )
            )

        return agents

    def convene(self, project_id: str, description: str) -> List[Dict[str, Any]]:
        agents = self._get_agents()
        # Lazy import of crewai constructs
        try:
            from crewai import Task, Crew, Process
        except ImportError:
            raise RuntimeError("crewai package required for convene; install or mock for tests.")

        task = Task(
            description=f"PROJECT: {project_id}\nDESC: {description}\nCreate 36 atomic tickets (3 per department). Return strict JSON array.",
            agent=agents[0],
            expected_output="JSON array of tickets with keys: ticket_id, department, title, instruction.",
        )
        crew = Crew(
            agents=agents, tasks=[task], process=Process.sequential, embedder=get_embedder_config()
        )

        raw_result = str(crew.kickoff())
        try:
            # First try direct JSON parsing
            try:
                return json.loads(raw_result)
            except Exception:
                # Fallback: find first JSON array in text
                match = re.search(r"(\[\s*\{.*?\}\s*\])", raw_result, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
                logger.error("Board returned non-JSON output: %s", raw_result[:2000])
                return []
        except Exception as e:
            logger.exception("JSON Parsing failed in Board Output: %s", e)
            return []


strategic_board = StrategicBoard()
