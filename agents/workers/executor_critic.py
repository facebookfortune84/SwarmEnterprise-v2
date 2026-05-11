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
