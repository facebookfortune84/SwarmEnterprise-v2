import logging
from typing import Any
from agents.tools.file_system import write_enterprise_file, read_enterprise_file
from agents.llm_config import get_local_brain_instance, get_embedder_config

logger = logging.getLogger("WorkerPair")

class AdversarialWorkerPair:
    """Level 3: Execution Tier. Lead Dev writes, Security Overseer audits."""
    def __init__(self):
        self.brain = None
        self.tools = [write_enterprise_file, read_enterprise_file]

    def process_ticket(self, ticket_id: str, file_path: str, instruction: str) -> str:
        # Lazy import crewai to avoid import-time dependency
        try:
            from crewai import Agent, Task, Crew, Process
        except ImportError:
            raise RuntimeError("crewai package required to run worker tasks; install or mock for tests.")

        brain = self.brain or get_local_brain_instance()
        embedder = get_embedder_config()

        executor = Agent(
            role="Lead Developer",
            goal=f"Write production code for {file_path}",
            backstory="You strictly write code and save it to the disk using tools.",
            tools=self.tools,
            llm=brain,
            verbose=True
        )

        critic = Agent(
            role="Security Overseer",
            goal=f"Audit the code in {file_path} for vulnerabilities.",
            backstory="You are a hostile auditor. You reject insecure code.",
            tools=self.tools,
            llm=brain,
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

        crew = Crew(agents=[executor, critic], tasks=[writing_task, audit_task], process=Process.sequential, embedder=embedder)
        return str(crew.kickoff())

execution_unit = AdversarialWorkerPair()
