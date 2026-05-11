import os

BASE_DIR = "/mnt/c/SwarmEnterprise_v2"

def write_file(path, content):
    full_path = os.path.join(BASE_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + "\n")
    print(f"[✓] Generated: {path}")

def generate_phase4():
    print("==========================================")
    print(" SWARM OS GENERATOR: PHASE 4 (EXECUTION)")
    print("==========================================")

    # 1. FILE SYSTEM TOOLS (How agents write code)
    write_file("agents/tools/file_system.py", r"""
from langchain.tools import tool
import os
import hashlib

BASE_OUTPUT_DIR = "/mnt/c/SwarmEnterprise_v2/output/src"

@tool("write_enterprise_file")
def write_enterprise_file(path: str, content: str) -> str:
    """Physically writes source code to disk."""
    try:
        full_path = os.path.join(BASE_OUTPUT_DIR, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        file_hash = hashlib.sha256(content.encode()).hexdigest()
        return f"SUCCESS: Wrote {path}. SHA256: {file_hash}"
    except Exception as e:
        return f"ERROR: Write failed. {str(e)}"

@tool("read_enterprise_file")
def read_enterprise_file(path: str) -> str:
    """Reads code from the disk for auditing."""
    try:
        full_path = os.path.join(BASE_OUTPUT_DIR, path)
        if not os.path.exists(full_path):
            return f"ERROR: {path} not found on disk."
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"ERROR: Read failed. {str(e)}"
""")

    # 2. ADVERSARIAL WORKER PAIRS
    write_file("agents/workers/executor_critic.py", r"""
import logging
from crewai import Agent, Task, Crew, Process
from agents.llm_config import LOCAL_BRAIN, EMBEDDER
from agents.tools.file_system import write_enterprise_file, read_enterprise_file

logger = logging.getLogger("WorkerPair")

class AdversarialWorkerPair:
    """Level 3: Execution Tier. Lead Dev writes, Security Overseer audits."""
    def __init__(self):
        self.brain = LOCAL_BRAIN
        self.tools = [write_enterprise_file, read_enterprise_file]

    def process_ticket(self, ticket_id: str, file_path: str, instruction: str):
        executor = Agent(
            role="Lead Developer",
            goal=f"Write production code for {file_path}",
            backstory="You strictly write code and save it to the disk using tools.",
            tools=self.tools,
            llm=self.brain,
            verbose=True
        )

        critic = Agent(
            role="Security Overseer",
            goal=f"Audit the code in {file_path} for vulnerabilities.",
            backstory="You are a hostile auditor. You reject insecure code.",
            tools=self.tools,
            llm=self.brain,
            verbose=True
        )

        writing_task = Task(
            description=f"Write code based on this instruction: {instruction}. Save it to {file_path}.",
            agent=executor,
            expected_output="Success message with SHA-256 hash."
        )

        audit_task = Task(
            description=f"Read {file_path} from disk and verify it meets enterprise standards.",
            agent=critic,
            expected_output="Pass/Fail audit report."
        )

        crew = Crew(agents=[executor, critic], tasks=[writing_task, audit_task], process=Process.sequential, embedder=EMBEDDER)
        return str(crew.kickoff())

execution_unit = AdversarialWorkerPair()
""")

    # 3. SWARM FACTORY (The Background Orchestrator)
    write_file("backend/core/factory.py", r"""
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
""")

    # 4. UPDATE API TO TRIGGER FACTORY
    write_file("backend/api/routes.py", r"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uuid
from backend.core.factory import swarm_factory

router = APIRouter(prefix="/api", tags=["Core Engine"])

class BuildRequest(BaseModel):
    name: str
    description: str
    stack: str

@router.post("/build")
async def trigger_build(request: BuildRequest, background_tasks: BackgroundTasks):
    try:
        project_id = f"PROJ-{uuid.uuid4().hex[:6].upper()}"
        
        # Trigger the AI Swarm in the background!
        background_tasks.add_task(
            swarm_factory.run_production_cycle,
            project_id=project_id,
            description=f"Stack: {request.stack}. Vibe: {request.description}"
        )
        
        return {"status": "Build Initialized", "project_id": project_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
""")

    print("\n[✓] PHASE 4 GENERATION COMPLETE.")

if __name__ == "__main__":
    generate_phase4()