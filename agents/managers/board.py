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

    @staticmethod
    def _default_tickets(project_id: str, description: str) -> List[Dict[str, Any]]:
        """Minimal default ticket set returned when the Board completely fails."""
        departments = [
            ("Engineering", "Set up project scaffolding and CI/CD pipeline"),
            ("Engineering", "Implement core business logic and API endpoints"),
            ("Engineering", "Write unit and integration tests"),
            ("DevOps", "Configure Docker and deployment infrastructure"),
            ("Security", "Perform security audit and add authentication"),
            ("QA", "Define acceptance criteria and test plan"),
        ]
        return [
            {
                "ticket_id": f"{project_id}-DEFAULT-{i + 1:02d}",
                "department": dept,
                "title": title,
                "instruction": f"{title}. Project: {project_id}. Context: {description[:200]}",
            }
            for i, (dept, title) in enumerate(departments)
        ]

    @staticmethod
    def _extract_json_array(raw: str) -> List[Dict[str, Any]] | None:
        """
        Try multiple strategies to extract a JSON array from a raw LLM string.
        Returns the parsed list or None if all strategies fail.
        """
        raw = raw.strip()

        # Strategy 1: direct parse
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 2: strip markdown code fences
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if fence_match:
            try:
                parsed = json.loads(fence_match.group(1).strip())
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

        # Strategy 3: greedy bracket scan — first '[' to last ']'
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end > start:
            try:
                parsed = json.loads(raw[start : end + 1])
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

        # Strategy 4: non-greedy regex array
        match = re.search(r"(\[\s*\{.*?\}\s*\])", raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1))
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

        return None

    def convene(self, project_id: str, description: str) -> List[Dict[str, Any]]:
        try:
            agents = self._get_agents()
        except Exception as e:
            logger.error("Board failed to create agents: %s", e)
            return self._default_tickets(project_id, description)

        # Lazy import of crewai constructs
        try:
            from crewai import Task, Crew, Process
        except ImportError:
            raise RuntimeError("crewai package required for convene; install or mock for tests.")

        task = Task(
            description=(
                f"PROJECT: {project_id}\nDESC: {description}\n"
                "Create 36 atomic tickets (3 per department). Return strict JSON array."
            ),
            agent=agents[0],
            expected_output="JSON array of tickets with keys: ticket_id, department, title, instruction.",
        )
        crew = Crew(
            agents=agents, tasks=[task], process=Process.sequential, embedder=get_embedder_config()
        )

        try:
            raw_result = str(crew.kickoff())
        except Exception as e:
            logger.exception("Board crew.kickoff() failed: %s", e)
            return self._default_tickets(project_id, description)

        parsed = self._extract_json_array(raw_result)
        if parsed is not None:
            return parsed

        logger.error(
            "Board returned non-JSON output after all extraction strategies; "
            "using default tickets. Raw (first 2000 chars): %s",
            raw_result[:2000],
        )
        return self._default_tickets(project_id, description)


strategic_board = StrategicBoard()
