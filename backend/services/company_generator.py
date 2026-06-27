"""
Company generation service - orchestrates the creation of complete applications
"""
import uuid
import logging
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.models import CompanyTenant, Ticket
from backend.db.session import SessionLocal
from agents.managers.board import strategic_board
from agents.workers.executor_critic import execution_unit

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
    Sovereign Factory Service for generating complete company applications.
    100% Operational, Zero-Cost FOSS implementation.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db or SessionLocal()

    async def generate_company(self, request: CompanyRequest) -> Dict[str, Any]:
        """
        Start company generation process (Entry point)
        """
        company_id = f"COMP-{uuid.uuid4().hex[:8].upper()}"
        slug = self._generate_slug(request.name)

        # Initialize tenant record in DB
        tenant = CompanyTenant(
            id=company_id,
            slug=slug,
            name=request.name,
            subdomain=f"{slug}.{os.getenv('TECH_DOMAIN', 'realms2riches.tech')}",
            status=GenerationStatus.PENDING.value,
            metadata_json=json.dumps(
                CompanyMetadata(
                    tech_stack=request.tech_stack.value,
                    features=request.features,
                    template_version="1.0.0",
                ).model_dump()
            ),
        )

        try:
            self.db.add(tenant)
            self.db.commit()
            self.db.refresh(tenant)

            # Execute generation pipeline
            # Note: In a production scale env, this should be moved to a Celery/Redis queue.
            # For 100% completion in this sovereign setup, we execute the flow.
            await self._execute_generation(tenant.id, request)

            return {
                "company_id": tenant.id,
                "status": tenant.status,
                "message": "Company generation cycle executed",
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to initiate company generation: {e}")
            raise

    async def _execute_generation(self, tenant_id: str, request: CompanyRequest):
        """
        The full autonomous loop: Vibe -> Board -> Workers -> Complete.
        """
        try:
            await self._update_status(tenant_id, GenerationStatus.INITIALIZING)

            # Step 1: Strategic Board convenes to create tickets
            await self._update_status(tenant_id, GenerationStatus.GENERATING_TICKETS)
            vibe = f"Project: {request.name}. Stack: {request.tech_stack.value}. Description: {request.description}. Features: {', '.join(request.features)}"
            tickets_data = strategic_board.convene(tenant_id, vibe)

            if not tickets_data:
                raise RuntimeError("Strategic Board failed to generate tickets")

            # Persist tickets and update metadata
            generated_tickets = []
            for t_data in tickets_data:
                ticket = Ticket(
                    project_id=tenant_id,
                    department=t_data.get("department", "Engineering"),
                    title=t_data.get("title", "Task"),
                    instruction=t_data.get("instruction", ""),
                )
                self.db.add(ticket)
                generated_tickets.append(ticket)

            self.db.commit()

            # Update Metadata
            tenant = self.db.query(CompanyTenant).filter_by(id=tenant_id).first()
            meta_data = json.loads(tenant.metadata_json)
            meta_data["tickets_created"] = len(generated_tickets)
            tenant.metadata_json = json.dumps(meta_data)
            self.db.commit()

            # Step 2: Execute tickets with Adversarial Worker Pair
            await self._update_status(tenant_id, GenerationStatus.EXECUTING_TICKETS)
            generated_files = []

            for ticket in generated_tickets:
                # Determine file path based on title/instruction or board output
                file_path = ticket.title.replace(" ", "_").lower()
                if not file_path.endswith((".py", ".tsx", ".js", ".html")):
                    file_path += ".py"

                result = execution_unit.process_ticket(
                    ticket_id=ticket.id, file_path=file_path, instruction=ticket.instruction
                )

                if "Pass" in result or "SUCCESS" in result:
                    ticket.status = "COMPLETED"
                    generated_files.append(file_path)
                else:
                    ticket.status = "FAILED"

                self.db.commit()

            # Step 3: Packaging & Completion
            await self._update_status(tenant_id, GenerationStatus.PACKAGING)

            # Update final metadata
            tenant = self.db.query(CompanyTenant).filter_by(id=tenant_id).first()
            meta_data = json.loads(tenant.metadata_json)
            meta_data["tickets_completed"] = len(
                [t for t in generated_tickets if t.status == "COMPLETED"]
            )
            meta_data["generated_files"] = generated_files
            tenant.metadata_json = json.dumps(meta_data)

            tenant.status = GenerationStatus.COMPLETED.value
            self.db.commit()

            logger.info(f"Sovereign Factory completed generation for {tenant_id}")

        except Exception as e:
            logger.error(f"Sovereign Factory failed for {tenant_id}: {str(e)}")
            await self._update_status(tenant_id, GenerationStatus.FAILED, error_msg=str(e))

    async def _update_status(self, tenant_id: str, status: GenerationStatus, error_msg: str = None):
        tenant = self.db.query(CompanyTenant).filter_by(id=tenant_id).first()
        if tenant:
            tenant.status = status.value
            if error_msg:
                tenant.last_error = error_msg
            tenant.updated_at = datetime.utcnow()
            self.db.commit()

    def _generate_slug(self, name: str) -> str:
        import re

        slug = name.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        return slug.strip("-")

    def get_generation_status(self, company_id: str) -> Optional[Dict[str, Any]]:
        tenant = self.db.query(CompanyTenant).filter_by(id=company_id).first()
        if not tenant:
            return None
        return {
            "id": tenant.id,
            "status": tenant.status,
            "last_error": tenant.last_error,
            "metadata": json.loads(tenant.metadata_json) if tenant.metadata_json else {},
        }
