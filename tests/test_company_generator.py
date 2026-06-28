"""
Unit tests for Company Generator Service
"""
import pytest
import json
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.db.models import CompanyTenant, Ticket
from backend.services.company_generator import (
    CompanyGenerator,
    CompanyRequest,
    TechStack,
    GenerationStatus,
)


class TestCompanyGenerator:
    """Test suite for CompanyGenerator"""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        """Set up in-memory database for testing"""
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        yield
        Base.metadata.drop_all(self.engine)

    @pytest.fixture
    def db_session(self):
        """Get a database session"""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    @pytest.fixture
    def generator(self, db_session):
        """Create a CompanyGenerator instance for testing"""
        return CompanyGenerator(db=db_session)

    @pytest.fixture
    def sample_request(self):
        """Sample company generation request"""
        return CompanyRequest(
            name="Test Company",
            description="A test company for unit testing",
            tech_stack=TechStack.FASTAPI_REACT_POSTGRES,
            features=["authentication", "api", "database"],
            user_id="user123",
        )

    @pytest.mark.asyncio
    async def test_generate_company_initiation(self, generator, sample_request):
        """Test company generation initiation"""
        # Mock _execute_generation to avoid slow agent calls
        with patch.object(generator, "_execute_generation", return_value=None):
            result = await generator.generate_company(sample_request)

            assert result is not None
            assert "company_id" in result
            assert "status" in result
            assert result["status"] == GenerationStatus.PENDING.value

            # Check DB record
            tenant = generator.db.query(CompanyTenant).filter_by(id=result["company_id"]).first()
            assert tenant is not None
            assert tenant.name == sample_request.name
            assert tenant.slug == "test-company"

    @pytest.mark.asyncio
    async def test_generate_slug(self, generator):
        """Test slug generation from company name"""
        slug1 = generator._generate_slug("Test Company")
        slug2 = generator._generate_slug("My Awesome App!")
        slug3 = generator._generate_slug("  Spaces   Everywhere  ")

        assert slug1 == "test-company"
        assert slug2 == "my-awesome-app"
        assert slug3 == "spaces-everywhere"

    def test_get_generation_status(self, generator, db_session):
        """Test getting status of generation"""
        company_id = "COMP-123"
        tenant = CompanyTenant(
            id=company_id,
            slug="test",
            name="Test",
            subdomain="test.example.com",
            status=GenerationStatus.PENDING.value,
            metadata_json=json.dumps({"test": "data"}),
        )
        db_session.add(tenant)
        db_session.commit()

        status = generator.get_generation_status(company_id)

        assert status is not None
        assert status["id"] == company_id
        assert status["status"] == GenerationStatus.PENDING.value
        assert status["metadata"] == {"test": "data"}

    @pytest.mark.asyncio
    async def test_update_status(self, generator, db_session):
        """Test status update functionality"""
        company_id = "COMP-123"
        tenant = CompanyTenant(
            id=company_id,
            slug="test",
            name="Test",
            subdomain="test.example.com",
            status=GenerationStatus.PENDING.value,
        )
        db_session.add(tenant)
        db_session.commit()

        await generator._update_status(company_id, GenerationStatus.INITIALIZING)

        # Refresh from DB
        db_session.refresh(tenant)
        assert tenant.status == GenerationStatus.INITIALIZING.value

    @pytest.mark.asyncio
    async def test_execute_generation_flow(self, generator, sample_request):
        """Test the full generation flow with mocked agents.

        generate_company() calls _execute_generation() inline, so we only invoke
        generate_company() once inside the mock context — calling _execute_generation()
        a second time would double the ticket count.
        """
        mock_tickets = [
            {"department": "Engineering", "title": "Setup", "instruction": "Initial setup"},
            {"department": "Engineering", "title": "API", "instruction": "Create API"},
        ]

        with patch(
            "backend.services.company_generator.strategic_board.convene",
            return_value=mock_tickets,
        ), patch(
            "backend.services.company_generator.execution_unit.process_ticket",
            return_value="SUCCESS: File created",
        ):
            # generate_company() already invokes _execute_generation() internally
            result = await generator.generate_company(sample_request)
            company_id = result["company_id"]

            # Check DB state — generation ran exactly once
            tenant = generator.db.query(CompanyTenant).filter_by(id=company_id).first()
            assert tenant.status == GenerationStatus.COMPLETED.value

            metadata = json.loads(tenant.metadata_json)
            assert metadata["tickets_created"] == 2
            assert metadata["tickets_completed"] == 2
            assert len(metadata["generated_files"]) == 2

            # Exactly 2 tickets persisted for this company
            tickets = generator.db.query(Ticket).filter_by(project_id=company_id).all()
            assert len(tickets) == 2
            for t in tickets:
                assert t.status == "COMPLETED"


# Made with Bob
