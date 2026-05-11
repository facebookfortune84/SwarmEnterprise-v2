import os
import json

BASE_DIR = "/mnt/c/SwarmEnterprise_v2"
REGISTRY_PATH = os.path.join(BASE_DIR, "assets/registry.json")

def load_registry():
    with open(REGISTRY_PATH, 'r') as f:
        return json.load(f)

def write_file(path, content):
    full_path = os.path.join(BASE_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + "\n")
    print(f"[✓] Generated: {path}")

def generate_core():
    print("==========================================")
    print(" SWARM OS GENERATOR: PHASE 1 (CORE ENGINE)")
    print("==========================================")
    
    registry = load_registry()
    
    # 1. LLM CONFIGURATION (FOSS Local Only)
    write_file("agents/llm_config.py", """
import os
import logging
from langchain_community.chat_models import ChatOpenAI

logger = logging.getLogger("SwarmBrain")

class SwarmBrain:
    """
    Sovereign FOSS Controller.
    Forces all agent traffic through the local Ollama instance.
    """
    @staticmethod
    def get_local_brain(model_name="llama3.2:3b", temperature=0.1, timeout=900):
        gateway_ip = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
        return ChatOpenAI(
            api_key="SOVEREIGN_LOCAL",
            base_url=f"{gateway_ip}/v1",
            model=model_name,
            temperature=temperature,
            request_timeout=timeout,
            max_retries=3
        )
        
    @staticmethod
    def get_embedder():
        gateway_ip = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
        return {
            "provider": "ollama",
            "config": {"model": "nomic-embed-text:latest", "base_url": gateway_ip}
        }

LOCAL_BRAIN = SwarmBrain.get_local_brain()
EMBEDDER = SwarmBrain.get_embedder()
""")

    # 2. THE BOARD OF DIRECTORS
    write_file("agents/managers/board.py", """
import json
import re
import logging
from typing import List, Dict, Any
from crewai import Agent, Task, Crew, Process
from agents.llm_config import LOCAL_BRAIN, EMBEDDER

logger = logging.getLogger("SwarmBoard")

class StrategicBoard:
    """Level 1: 12-Manager Oracle-Backed Board"""
    
    def __init__(self):
        self.brain = LOCAL_BRAIN
        self.roles =[
            "CTO", "CPO", "Chief Architect", "Security Director", 
            "DevOps Director", "QA Director", "UI/UX Director", 
            "Marketing Director", "Outreach Director", "Replicator Lead", 
            "Documentation Manager", "Compliance Manager"
        ]

    def _get_agents(self) -> List[Agent]:
        return[
            Agent(
                role=role,
                goal=f"Decompose the project vibe into technical tickets from the perspective of a {role}.",
                backstory=f"You are the {role} of a Sovereign Swarm. You operate using FOSS principles. You output JSON tickets.",
                llm=self.brain,
                verbose=True
            ) for role in self.roles
        ]

    def convene(self, project_id: str, description: str) -> List[Dict[str, Any]]:
        agents = self._get_agents()
        task = Task(
            description=f"PROJECT: {project_id}\\nDESC: {description}\\nCreate 36 atomic tickets (3 per department). Return strict JSON array.",
            agent=agents[0],
            expected_output="JSON array of tickets with keys: ticket_id, department, title, instruction."
        )
        crew = Crew(agents=agents, tasks=[task], process=Process.sequential, embedder=EMBEDDER)
        
        raw_result = str(crew.kickoff())
        try:
            match = re.search(r'\[\s*\{.*\}\s*\]', raw_result, re.DOTALL)
            return json.loads(match.group()) if match else[]
        except:
            logger.error("JSON Parsing failed in Board Output.")
            return[]

strategic_board = StrategicBoard()
""")

    # 3. LINEAR ENGINE (DATABASE)
    write_file("backend/db/linear_engine.py", """
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Ticket(Base):
    __tablename__ = 'tickets'
    id = Column(String, primary_key=True)
    project_id = Column(String)
    department = Column(String)
    title = Column(String)
    instruction = Column(Text)
    status = Column(String, default="OPEN")
    created_at = Column(DateTime, default=datetime.utcnow)

class LinearEngine:
    """Ticket persistence for the swarm"""
    def __init__(self):
        self.engine = create_engine("sqlite:////mnt/c/SwarmEnterprise_v2/pg_data/swarm_tickets.db")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create_ticket(self, project_id, dept, title, instruction):
        session = self.Session()
        t = Ticket(id=uuid.uuid4().hex[:8].upper(), project_id=project_id, department=dept, title=title, instruction=instruction)
        session.add(t)
        session.commit()
        session.close()

swarm_db = LinearEngine()
""")

    print("\n[✓] PHASE 1 GENERATION COMPLETE.")

if __name__ == "__main__":
    generate_core()