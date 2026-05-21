import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _paths import output_src_dir, repo_root  # noqa: E402

BASE_DIR = repo_root()
OUT_SRC = output_src_dir().replace("\\", "/")


def write_file(path, content):
    full_path = os.path.join(BASE_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"[OK] Generated: {path}")


def generate_phase4():
    print("==========================================")
    print(" SWARM OS GENERATOR: PHASE 4 (EXECUTION)")
    print("==========================================")

    write_file(
        "agents/tools/file_system.py",
        f"""
import hashlib
import os
from langchain.tools import tool

BASE_OUTPUT_DIR = os.getenv("SWARM_OUTPUT_SRC_DIR", "{OUT_SRC}")


@tool("write_enterprise_file")
def write_enterprise_file(path: str, content: str) -> str:
    try:
        full_path = os.path.join(BASE_OUTPUT_DIR, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        file_hash = hashlib.sha256(content.encode()).hexdigest()
        return f"SUCCESS: Wrote {{path}}. SHA256: {{file_hash}}"
    except Exception as e:
        return f"ERROR: Write failed. {{e}}"


@tool("read_enterprise_file")
def read_enterprise_file(path: str) -> str:
    try:
        full_path = os.path.join(BASE_OUTPUT_DIR, path)
        if not os.path.exists(full_path):
            return f"ERROR: {{path}} not found on disk."
        with open(full_path, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"ERROR: Read failed. {{e}}"
""",
    )

    write_file(
        "agents/workers/executor_critic.py",
        """
import logging
from crewai import Agent, Task, Crew, Process
from agents.llm_config import LOCAL_BRAIN, EMBEDDER
from agents.tools.file_system import write_enterprise_file, read_enterprise_file

logger = logging.getLogger("WorkerPair")


class AdversarialWorkerPair:
    def __init__(self):
        self.brain = LOCAL_BRAIN
        self.tools = [write_enterprise_file, read_enterprise_file]

    def process_ticket(self, ticket_id: str, file_path: str, instruction: str):
        executor = Agent(
            role="Lead Developer",
            goal=f"Write production code for {file_path}",
            backstory="Write code and save it using tools.",
            tools=self.tools,
            llm=self.brain,
            verbose=True,
        )
        critic = Agent(
            role="Security Overseer",
            goal=f"Audit the code in {file_path} for vulnerabilities.",
            backstory="Reject insecure code.",
            tools=self.tools,
            llm=self.brain,
            verbose=True,
        )
        writing_task = Task(
            description=f"Write code: {instruction}. Save to {file_path}.",
            agent=executor,
            expected_output="Success message with SHA-256 hash.",
        )
        audit_task = Task(
            description=f"Read {file_path} and verify enterprise standards.",
            agent=critic,
            expected_output="Pass/Fail audit report.",
        )
        crew = Crew(
            agents=[executor, critic],
            tasks=[writing_task, audit_task],
            process=Process.sequential,
            embedder=EMBEDDER,
        )
        return str(crew.kickoff())


execution_unit = AdversarialWorkerPair()
""",
    )

    write_file(
        "backend/core/factory.py",
        """
import logging
from agents.managers.board import strategic_board
from backend.db.linear_engine import swarm_db

logger = logging.getLogger("SwarmFactory")


class SwarmFactory:
    def run_production_cycle(self, project_id: str, description: str):
        logger.info("FACTORY: Convening Board for %s...", project_id)
        plan = strategic_board.convene(project_id, description)
        for task in plan:
            swarm_db.create_ticket(
                project_id=project_id,
                dept=task.get("department", "Engineering"),
                title=task.get("title", "Task"),
                instruction=task.get("instruction", ""),
            )
        logger.info("FACTORY: %s tickets created.", len(plan))
        return {"status": "success", "tickets_generated": len(plan)}


swarm_factory = SwarmFactory()
""",
    )

    write_file(
        "backend/api/routes.py",
        """
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
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
        background_tasks.add_task(
            swarm_factory.run_production_cycle,
            project_id=project_id,
            description=f"Stack: {request.stack}. Vibe: {request.description}",
        )
        return {"status": "Build Initialized", "project_id": project_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
""",
    )

    os.makedirs(OUT_SRC, exist_ok=True)
    print("\n[OK] PHASE 4 GENERATION COMPLETE.")


if __name__ == "__main__":
    generate_phase4()
