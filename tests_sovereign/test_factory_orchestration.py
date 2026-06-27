import pytest
import json
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.services.company_generator import (
    CompanyGenerator,
    CompanyRequest,
    TechStack,
    GenerationStatus,
)

# Setup Test DB
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.mark.asyncio
async def test_full_factory_pipeline_orchestration(db):
    """
    Tests the 100% complete orchestration loop of the Sovereign Factory.
    Mocks the heavy LLM/CrewAI calls to verify the state machine and DB persistence.
    """
    generator = CompanyGenerator(db)
    request = CompanyRequest(
        name="Test SaaS",
        description="A simple task manager",
        tech_stack=TechStack.FASTAPI_REACT_POSTGRES,
        features=["auth", "tasks"],
        user_id="user-123",
    )

    # Mock Strategic Board
    mock_tickets = [
        {"department": "Engineering", "title": "Setup DB", "instruction": "Create models.py"},
        {"department": "Engineering", "title": "Setup API", "instruction": "Create main.py"},
    ]

    # Mock Worker Execution
    mock_worker_result = "SUCCESS: Code written and audited. Pass."

    with patch("agents.managers.board.strategic_board.convene", return_value=mock_tickets), patch(
        "agents.workers.executor_critic.execution_unit.process_ticket",
        return_value=mock_worker_result,
    ):
        result = await generator.generate_company(request)

        assert result["company_id"].startswith("COMP-")

        # Verify DB state after completion
        from backend.db.models import CompanyTenant, Ticket

        tenant = db.query(CompanyTenant).filter_by(id=result["company_id"]).first()
        assert tenant.status == GenerationStatus.COMPLETED.value

        tickets = db.query(Ticket).filter_by(project_id=tenant.id).all()
        assert len(tickets) == 2
        assert all(t.status == "COMPLETED" for t in tickets)

        meta = json.loads(tenant.metadata_json)
        assert meta["tickets_created"] == 2
        assert meta["tickets_completed"] == 2
        assert "setup_db.py" in meta["generated_files"]
        assert "setup_api.py" in meta["generated_files"]


@pytest.mark.asyncio
async def test_factory_failure_handling(db):
    """
    Tests that the factory correctly handles and persists failures.
    """
    generator = CompanyGenerator(db)
    request = CompanyRequest(
        name="Fail Project",
        description="This will fail",
        tech_stack=TechStack.NODEJS_TAILWIND_MONGO,
        user_id="user-123",
    )

    with patch(
        "agents.managers.board.strategic_board.convene", side_effect=Exception("LLM Timeout")
    ):
        result = await generator.generate_company(request)

        from backend.db.models import CompanyTenant

        tenant = db.query(CompanyTenant).filter_by(id=result["company_id"]).first()
        assert tenant.status == GenerationStatus.FAILED.value
        assert "LLM Timeout" in tenant.last_error
