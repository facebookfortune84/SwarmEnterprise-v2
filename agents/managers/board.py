import json
import logging
from typing import List, Dict, Any
from crewai import Agent, Task, Crew, Process
from agents.llm_config import LOCAL_BRAIN, EMBEDDER
from langchain_ollama import OllamaLLM

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
            description=f"PROJECT: {project_id}\nDESC: {description}\nCreate 36 atomic tickets (3 per department). Return strict JSON array.",
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
