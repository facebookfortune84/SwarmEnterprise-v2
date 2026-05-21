import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _paths import output_src_dir, repo_root  # noqa: E402

BASE_DIR = repo_root()
REGISTRY_PATH = os.path.join(BASE_DIR, "assets", "registry.json")
PG_DB = os.path.join(BASE_DIR, "pg_data", "swarm_tickets.db").replace("\\", "/")


def load_registry():
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def write_file(path, content):
    full_path = os.path.join(BASE_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"[OK] Generated: {path}")


def generate_core():
    print("==========================================")
    print(" SWARM OS GENERATOR: PHASE 1 (CORE ENGINE)")
    print("==========================================")

    load_registry()

    write_file(
        "agents/llm_config.py",
        """
import os
import logging
from langchain_community.chat_models import ChatOpenAI

logger = logging.getLogger("SwarmBrain")


class SwarmBrain:
    \"\"\"Sovereign FOSS controller; routes agents through local Ollama.\"\"\"

    @staticmethod
    def get_local_brain(model_name="llama3.2:3b", temperature=0.1, timeout=900):
        gateway_ip = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
        return ChatOpenAI(
            api_key="SOVEREIGN_LOCAL",
            base_url=f"{gateway_ip}/v1",
            model=model_name,
            temperature=temperature,
            request_timeout=timeout,
            max_retries=3,
        )

    @staticmethod
    def get_embedder():
        gateway_ip = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
        return {
            "provider": "ollama",
            "config": {"model": "nomic-embed-text:latest", "base_url": gateway_ip},
        }


LOCAL_BRAIN = SwarmBrain.get_local_brain()
EMBEDDER = SwarmBrain.get_embedder()
""",
    )

    write_file(
        "agents/managers/board.py",
        """
import json
import re
import logging
from typing import List, Dict, Any
from crewai import Agent, Task, Crew, Process
from agents.llm_config import LOCAL_BRAIN, EMBEDDER

logger = logging.getLogger("SwarmBoard")


class StrategicBoard:
    \"\"\"Level 1: board decomposes directives into tickets.\"\"\"

    def __init__(self):
        self.brain = LOCAL_BRAIN
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

    def _get_agents(self) -> List[Agent]:
        return [
            Agent(
                role=role,
                goal=f"Decompose the project vibe into technical tickets as {role}.",
                backstory=f"You are the {role} of a Sovereign Swarm. Output JSON tickets.",
                llm=self.brain,
                verbose=True,
            )
            for role in self.roles
        ]

    def convene(self, project_id: str, description: str) -> List[Dict[str, Any]]:
        agents = self._get_agents()
        task = Task(
            description=(
                f"PROJECT: {project_id}\\nDESC: {description}\\n"
                "Create 36 atomic tickets (3 per department). Return strict JSON array."
            ),
            agent=agents[0],
            expected_output="JSON array of tickets with keys: ticket_id, department, title, instruction.",
        )
        crew = Crew(agents=agents, tasks=[task], process=Process.sequential, embedder=EMBEDDER)
        raw_result = str(crew.kickoff())
        try:
            match = re.search(r"\\[\\s*\\{.*\\}\\s*\\]", raw_result, re.DOTALL)
            return json.loads(match.group()) if match else []
        except Exception:
            logger.error("JSON parsing failed in board output.")
            return []


strategic_board = StrategicBoard()
""",
    )

    write_file(
        "backend/db/linear_engine.py",
        f"""
import os
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(String, primary_key=True)
    project_id = Column(String)
    department = Column(String)
    title = Column(String)
    instruction = Column(Text)
    status = Column(String, default="OPEN")
    created_at = Column(DateTime, default=datetime.utcnow)


class LinearEngine:
    \"\"\"Ticket persistence for the swarm.\"\"\"

    def __init__(self):
        default_db = "sqlite:///{PG_DB}"
        self.engine = create_engine(os.getenv("SWARM_DB_URL", default_db))
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create_ticket(self, project_id, dept, title, instruction):
        session = self.Session()
        ticket = Ticket(
            id=uuid.uuid4().hex[:8].upper(),
            project_id=project_id,
            department=dept,
            title=title,
            instruction=instruction,
        )
        session.add(ticket)
        session.commit()
        session.close()


swarm_db = LinearEngine()
""",
    )

    os.makedirs(output_src_dir(), exist_ok=True)
    print("\n[OK] PHASE 1 GENERATION COMPLETE.")


if __name__ == "__main__":
    generate_core()
