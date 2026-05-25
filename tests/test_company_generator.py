"""
Unit tests for Company Generator Service
"""
import pytest
from backend.services.company_generator import (
    CompanyGenerator,
    CompanyRequest,
    TechStack,
    GenerationStatus,
    CompanyMetadata,
)


class TestCompanyGenerator:
    """Test suite for CompanyGenerator"""
    
    @pytest.fixture
    def generator(self):
        """Create a CompanyGenerator instance for testing"""
        return CompanyGenerator()
    
    @pytest.fixture
    def sample_request(self):
        """Sample company generation request"""
        return CompanyRequest(
            name="Test Company",
            description="A test company for unit testing",
            tech_stack=TechStack.FASTAPI_REACT_POSTGRES,
            features=["authentication", "api", "database"],
            user_id="user123"
        )
    
    @pytest.mark.asyncio
    async def test_generate_company(self, generator, sample_request):
        """Test company generation initiation"""
        result = await generator.generate_company(sample_request)
        
        assert result is not None
        assert "company_id" in result
        assert "status" in result
        assert "estimated_time_minutes" in result
        assert "message" in result
        assert result["status"] == GenerationStatus.PENDING.value
        assert isinstance(result["estimated_time_minutes"], int)
    
    @pytest.mark.asyncio
    async def test_generate_company_creates_record(self, generator, sample_request):
        """Test that generation creates a company record"""
        result = await generator.generate_company(sample_request)
        company_id = result["company_id"]
        
        # Check that company was stored
        assert company_id in generator.generations
        company = generator.generations[company_id]
        
        assert company["name"] == sample_request.name
        assert company["description"] == sample_request.description
        assert company["tech_stack"] == sample_request.tech_stack.value
        assert company["user_id"] == sample_request.user_id
        assert company["status"] == GenerationStatus.PENDING.value
    
    @pytest.mark.asyncio
    async def test_generate_slug(self, generator):
        """Test slug generation from company name"""
        slug1 = generator._generate_slug("Test Company")
        slug2 = generator._generate_slug("My Awesome App!")
        slug3 = generator._generate_slug("  Spaces   Everywhere  ")
        
        assert slug1 == "test-company"
        assert slug2 == "my-awesome-app"
        assert slug3 == "spaces-everywhere"
    
    @pytest.mark.asyncio
    async def test_estimate_generation_time(self, generator):
        """Test generation time estimation"""
        request1 = CompanyRequest(
            name="Simple App",
            description="Simple",
            tech_stack=TechStack.FASTAPI_REACT_POSTGRES,
            features=[],
            user_id="user123"
        )
        
        request2 = CompanyRequest(
            name="Complex App",
            description="Complex",
            tech_stack=TechStack.FASTAPI_REACT_POSTGRES,
            features=["auth", "api", "db", "cache", "queue"],
            user_id="user123"
        )
        
        time1 = generator._estimate_generation_time(request1)
        time2 = generator._estimate_generation_time(request2)
        
        assert time1 == 5  # Base time only
        assert time2 == 15  # Base + 5 features * 2 minutes
        assert time2 > time1
    
    def test_get_generation_status_exists(self, generator):
        """Test getting status of existing generation"""
        company_id = "test-123"
        generator.generations[company_id] = {
            "id": company_id,
            "status": GenerationStatus.PENDING.value,
            "name": "Test Company"
        }
        
        status = generator.get_generation_status(company_id)
        
        assert status is not None
        assert status["id"] == company_id
        assert status["status"] == GenerationStatus.PENDING.value
    
    def test_get_generation_status_not_found(self, generator):
        """Test getting status of non-existent generation"""
        status = generator.get_generation_status("nonexistent")
        
        assert status is None
    
    def test_cancel_generation_success(self, generator):
        """Test cancelling an ongoing generation"""
        company_id = "test-123"
        generator.generations[company_id] = {
            "id": company_id,
            "status": GenerationStatus.GENERATING_TICKETS.value,
            "name": "Test Company"
        }
        
        result = generator.cancel_generation(company_id)
        
        assert result is True
        assert generator.generations[company_id]["status"] == GenerationStatus.FAILED.value
        assert "error" in generator.generations[company_id]
        assert generator.generations[company_id]["error"] == "Cancelled by user"
    
    def test_cancel_generation_already_completed(self, generator):
        """Test that completed generations cannot be cancelled"""
        company_id = "test-123"
        generator.generations[company_id] = {
            "id": company_id,
            "status": GenerationStatus.COMPLETED.value,
            "name": "Test Company"
        }
        
        result = generator.cancel_generation(company_id)
        
        assert result is True  # Returns True but doesn't change status
        assert generator.generations[company_id]["status"] == GenerationStatus.COMPLETED.value
    
    def test_cancel_generation_not_found(self, generator):
        """Test cancelling non-existent generation"""
        result = generator.cancel_generation("nonexistent")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_update_status(self, generator):
        """Test status update functionality"""
        company_id = "test-123"
        generator.generations[company_id] = {
            "id": company_id,
            "status": GenerationStatus.PENDING.value,
            "name": "Test Company"
        }
        
        await generator._update_status(company_id, GenerationStatus.INITIALIZING)
        
        assert generator.generations[company_id]["status"] == GenerationStatus.INITIALIZING.value
        assert "updated_at" in generator.generations[company_id]
    
    @pytest.mark.asyncio
    async def test_load_template(self, generator):
        """Test template loading"""
        template = await generator._load_template(TechStack.FASTAPI_REACT_POSTGRES)
        
        assert template is not None
        assert "name" in template
        assert "version" in template
        assert "files" in template
        assert template["name"] == TechStack.FASTAPI_REACT_POSTGRES.value
    
    @pytest.mark.asyncio
    async def test_generate_tickets(self, generator, sample_request):
        """Test ticket generation"""
        template = await generator._load_template(sample_request.tech_stack)
        tickets = await generator._generate_tickets(sample_request, template)
        
        assert tickets is not None
        assert isinstance(tickets, list)
        assert len(tickets) > 0
        
        # Check ticket structure
        for ticket in tickets:
            assert "ticket_id" in ticket
            assert "department" in ticket
            assert "title" in ticket
            assert "instruction" in ticket
            assert "priority" in ticket
    
    @pytest.mark.asyncio
    async def test_execute_tickets(self, generator):
        """Test ticket execution"""
        tickets = [
            {
                "ticket_id": "TKT-001",
                "department": "Engineering",
                "title": "Setup project",
                "instruction": "Create project structure",
                "priority": "high"
            }
        ]
        
        files = await generator._execute_tickets(tickets)
        
        assert files is not None
        assert isinstance(files, list)
        assert len(files) > 0
    
    @pytest.mark.asyncio
    async def test_package_code(self, generator):
        """Test code packaging"""
        company_id = "test-123"
        files = ["backend/main.py", "frontend/App.tsx", "README.md"]
        
        package_path = await generator._package_code(company_id, files)
        
        assert package_path is not None
        assert isinstance(package_path, str)
        assert company_id in package_path
        assert package_path.endswith(".zip")
    
    @pytest.mark.asyncio
    async def test_upload_to_storage(self, generator):
        """Test storage upload"""
        company_id = "test-123"
        package_path = f"/tmp/{company_id}.zip"
        
        storage_path = await generator._upload_to_storage(company_id, package_path)
        
        assert storage_path is not None
        assert isinstance(storage_path, str)
        assert company_id in storage_path
    
    def test_company_metadata_structure(self):
        """Test CompanyMetadata structure"""
        metadata = CompanyMetadata(
            tech_stack="fastapi-react-postgres",
            features=["auth", "api"],
            template_version="1.0.0",
            generated_files=["main.py", "app.tsx"],
            tickets_created=5,
            tickets_completed=5
        )
        
        assert metadata.tech_stack == "fastapi-react-postgres"
        assert len(metadata.features) == 2
        assert metadata.template_version == "1.0.0"
        assert len(metadata.generated_files) == 2
        assert metadata.tickets_created == 5
        assert metadata.tickets_completed == 5
    
    def test_tech_stack_enum_values(self):
        """Test TechStack enum values"""
        assert TechStack.FASTAPI_REACT_POSTGRES.value == "fastapi-react-postgres"
        assert TechStack.NODEJS_TAILWIND_MONGO.value == "nodejs-tailwind-mongo"
        assert TechStack.DJANGO_VUE_MYSQL.value == "django-vue-mysql"
    
    def test_generation_status_enum_values(self):
        """Test GenerationStatus enum values"""
        assert GenerationStatus.PENDING.value == "pending"
        assert GenerationStatus.INITIALIZING.value == "initializing"
        assert GenerationStatus.GENERATING_TICKETS.value == "generating_tickets"
        assert GenerationStatus.EXECUTING_TICKETS.value == "executing_tickets"
        assert GenerationStatus.PACKAGING.value == "packaging"
        assert GenerationStatus.COMPLETED.value == "completed"
        assert GenerationStatus.FAILED.value == "failed"
    
    @pytest.mark.asyncio
    async def test_company_request_validation(self):
        """Test CompanyRequest validation"""
        # Valid request
        request = CompanyRequest(
            name="Valid Company",
            description="Valid description",
            tech_stack=TechStack.FASTAPI_REACT_POSTGRES,
            features=["auth"],
            user_id="user123"
        )
        
        assert request.name == "Valid Company"
        assert request.tech_stack == TechStack.FASTAPI_REACT_POSTGRES
        assert len(request.features) == 1
    
    @pytest.mark.asyncio
    async def test_multiple_generations(self, generator):
        """Test handling multiple concurrent generations"""
        request1 = CompanyRequest(
            name="Company 1",
            description="First company",
            tech_stack=TechStack.FASTAPI_REACT_POSTGRES,
            features=[],
            user_id="user1"
        )
        
        request2 = CompanyRequest(
            name="Company 2",
            description="Second company",
            tech_stack=TechStack.NODEJS_TAILWIND_MONGO,
            features=[],
            user_id="user2"
        )
        
        result1 = await generator.generate_company(request1)
        result2 = await generator.generate_company(request2)
        
        assert result1["company_id"] != result2["company_id"]
        assert len(generator.generations) == 2
        assert result1["company_id"] in generator.generations
        assert result2["company_id"] in generator.generations


# Made with Bob