"""
Company generation service - orchestrates the creation of complete applications
"""
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class GenerationStatus(str, Enum):
    """Company generation status"""
    PENDING = "pending"
    INITIALIZING = "initializing"
    GENERATING_TICKETS = "generating_tickets"
    EXECUTING_TICKETS = "executing_tickets"
    PACKAGING = "packaging"
    COMPLETED = "completed"
    FAILED = "failed"


class TechStack(str, Enum):
    """Available technology stacks"""
    FASTAPI_REACT_POSTGRES = "fastapi-react-postgres"
    NODEJS_TAILWIND_MONGO = "nodejs-tailwind-mongo"
    DJANGO_VUE_MYSQL = "django-vue-mysql"


class CompanyRequest(BaseModel):
    """Company generation request schema"""
    name: str
    description: str
    tech_stack: TechStack
    features: List[str] = []
    user_id: str


class CompanyMetadata(BaseModel):
    """Company metadata"""
    tech_stack: str
    features: List[str]
    template_version: str
    generated_files: List[str] = []
    tickets_created: int = 0
    tickets_completed: int = 0


class CompanyGenerator:
    """
    Service for generating complete company applications
    
    This orchestrates the entire generation process:
    1. Initialize generation request
    2. Convene strategic board
    3. Generate tickets
    4. Execute tickets with worker agents
    5. Package the code
    6. Store in S3
    """
    
    def __init__(self, db_session=None, storage_service=None):
        """
        Initialize company generator
        
        Args:
            db_session: Database session (optional)
            storage_service: Storage service for file operations (optional)
        """
        self.db = db_session
        self.storage = storage_service
        self.generations = {}  # In-memory tracking (use Redis in production)
    
    async def generate_company(self, request: CompanyRequest) -> Dict[str, Any]:
        """
        Start company generation process
        
        Args:
            request: Company generation request
            
        Returns:
            Company generation info with ID and status
        """
        company_id = str(uuid.uuid4())
        slug = self._generate_slug(request.name)
        
        # Create company record
        company = {
            "id": company_id,
            "user_id": request.user_id,
            "name": request.name,
            "slug": slug,
            "description": request.description,
            "tech_stack": request.tech_stack.value,
            "status": GenerationStatus.PENDING.value,
            "metadata": CompanyMetadata(
                tech_stack=request.tech_stack.value,
                features=request.features,
                template_version="1.0.0"
            ).dict(),
            "generation_started_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store in memory (TODO: save to database)
        self.generations[company_id] = company
        
        # Start async generation process
        # TODO: Queue this as a background task
        # await self._execute_generation(company_id, request)
        
        logger.info(f"Company generation started: {company_id}")
        
        return {
            "company_id": company_id,
            "status": GenerationStatus.PENDING.value,
            "estimated_time_minutes": self._estimate_generation_time(request),
            "message": "Company generation started"
        }
    
    async def _execute_generation(self, company_id: str, request: CompanyRequest):
        """
        Execute the full generation pipeline
        
        Args:
            company_id: Company ID
            request: Generation request
        """
        try:
            # Update status: Initializing
            await self._update_status(company_id, GenerationStatus.INITIALIZING)
            
            # Step 1: Load template
            template = await self._load_template(request.tech_stack)
            
            # Step 2: Convene strategic board
            await self._update_status(company_id, GenerationStatus.GENERATING_TICKETS)
            tickets = await self._generate_tickets(request, template)
            
            # Update metadata
            company = self.generations[company_id]
            company["metadata"]["tickets_created"] = len(tickets)
            
            # Step 3: Execute tickets with worker agents
            await self._update_status(company_id, GenerationStatus.EXECUTING_TICKETS)
            generated_files = await self._execute_tickets(tickets)
            
            # Update metadata
            company["metadata"]["tickets_completed"] = len(tickets)
            company["metadata"]["generated_files"] = generated_files
            
            # Step 4: Package code
            await self._update_status(company_id, GenerationStatus.PACKAGING)
            package_path = await self._package_code(company_id, generated_files)
            
            # Step 5: Upload to storage
            storage_path = await self._upload_to_storage(company_id, package_path)
            company["storage_path"] = storage_path
            
            # Mark as completed
            await self._update_status(company_id, GenerationStatus.COMPLETED)
            company["generation_completed_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"Company generation completed: {company_id}")
            
        except Exception as e:
            logger.error(f"Company generation failed: {company_id} - {str(e)}")
            await self._update_status(company_id, GenerationStatus.FAILED)
            company = self.generations[company_id]
            company["error"] = str(e)
    
    async def _load_template(self, tech_stack: TechStack) -> Dict[str, Any]:
        """
        Load template configuration
        
        Args:
            tech_stack: Technology stack
            
        Returns:
            Template configuration
        """
        # TODO: Load from backend/templates/
        return {
            "name": tech_stack.value,
            "version": "1.0.0",
            "files": []
        }
    
    async def _generate_tickets(
        self,
        request: CompanyRequest,
        template: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate tickets using strategic board
        
        Args:
            request: Company request
            template: Template configuration
            
        Returns:
            List of tickets
        """
        # TODO: Integrate with agents/board.py
        # board = StrategicBoard()
        # tickets = await board.convene(request, template)
        
        # Mock tickets for now
        return [
            {
                "ticket_id": "TKT-001",
                "department": "Engineering",
                "title": "Set up project structure",
                "instruction": f"Create {request.tech_stack.value} project structure",
                "priority": "high"
            },
            {
                "ticket_id": "TKT-002",
                "department": "Engineering",
                "title": "Implement authentication",
                "instruction": "Add JWT-based authentication",
                "priority": "high"
            }
        ]
    
    async def _execute_tickets(self, tickets: List[Dict[str, Any]]) -> List[str]:
        """
        Execute tickets with worker agents
        
        Args:
            tickets: List of tickets
            
        Returns:
            List of generated file paths
        """
        # TODO: Integrate with agents/workers/
        # worker_pool = WorkerPool()
        # files = await worker_pool.execute_tickets(tickets)
        
        # Mock file list for now
        return [
            "backend/main.py",
            "backend/models.py",
            "backend/routes.py",
            "frontend/src/App.tsx",
            "docker-compose.yml",
            "README.md"
        ]
    
    async def _package_code(self, company_id: str, files: List[str]) -> str:
        """
        Package generated code into archive
        
        Args:
            company_id: Company ID
            files: List of generated files
            
        Returns:
            Path to package file
        """
        # TODO: Integrate with CodePackager
        # packager = CodePackager()
        # package_path = await packager.create_archive(company_id, files)
        
        return f"/tmp/{company_id}.zip"
    
    async def _upload_to_storage(self, company_id: str, package_path: str) -> str:
        """
        Upload package to S3/MinIO
        
        Args:
            company_id: Company ID
            package_path: Local package path
            
        Returns:
            Storage path
        """
        # TODO: Integrate with storage service
        # if self.storage:
        #     storage_path = await self.storage.upload(package_path, f"companies/{company_id}/source.zip")
        #     return storage_path
        
        return f"companies/{company_id}/source.zip"
    
    async def _update_status(self, company_id: str, status: GenerationStatus):
        """
        Update company generation status
        
        Args:
            company_id: Company ID
            status: New status
        """
        if company_id in self.generations:
            self.generations[company_id]["status"] = status.value
            self.generations[company_id]["updated_at"] = datetime.utcnow().isoformat()
    
    def get_generation_status(self, company_id: str) -> Optional[Dict[str, Any]]:
        """
        Get company generation status
        
        Args:
            company_id: Company ID
            
        Returns:
            Company info or None if not found
        """
        return self.generations.get(company_id)
    
    def cancel_generation(self, company_id: str) -> bool:
        """
        Cancel ongoing generation
        
        Args:
            company_id: Company ID
            
        Returns:
            True if cancelled, False if not found
        """
        if company_id in self.generations:
            company = self.generations[company_id]
            if company["status"] not in [GenerationStatus.COMPLETED.value, GenerationStatus.FAILED.value]:
                company["status"] = GenerationStatus.FAILED.value
                company["error"] = "Cancelled by user"
                return True
        return False
    
    def _generate_slug(self, name: str) -> str:
        """
        Generate URL-safe slug from company name
        
        Args:
            name: Company name
            
        Returns:
            URL-safe slug
        """
        import re
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')
        return slug
    
    def _estimate_generation_time(self, request: CompanyRequest) -> int:
        """
        Estimate generation time in minutes
        
        Args:
            request: Company request
            
        Returns:
            Estimated time in minutes
        """
        base_time = 5  # Base time for simple project
        feature_time = len(request.features) * 2  # 2 minutes per feature
        return base_time + feature_time

# Made with Bob
