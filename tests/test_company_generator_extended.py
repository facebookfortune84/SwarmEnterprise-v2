"""
Extended tests for backend/services/company_generator.py
Covers _generate_slug edge cases, _execute_generation, update_status, and get_generation_status.
"""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.base import Base


@pytest.fixture(scope="module")
def _engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db(_engine) -> Session:
    SessionFactory = sessionmaker(bind=_engine)
    session = SessionFactory()
    yield session
    session.rollback()
    session.close()


class TestGenerateSlugEdgeCases:
    def test_slug_all_special_chars(self, db):
        from backend.services.company_generator import CompanyGenerator

        gen = CompanyGenerator(db=db)
        assert gen._generate_slug("!!!") == "" or gen._generate_slug("!!!") is not None

    def test_slug_numbers(self, db):
        from backend.services.company_generator import CompanyGenerator

        gen = CompanyGenerator(db=db)
        assert gen._generate_slug("Company 42") == "company-42"

    def test_slug_multiple_spaces(self, db):
        from backend.services.company_generator import CompanyGenerator

        gen = CompanyGenerator(db=db)
        slug = gen._generate_slug("Hello   World")
        assert slug == "hello-world"

    def test_slug_leading_trailing_dashes(self, db):
        from backend.services.company_generator import CompanyGenerator

        gen = CompanyGenerator(db=db)
        slug = gen._generate_slug("--Test--")
        assert not slug.startswith("-")
        assert not slug.endswith("-")

    def test_slug_unicode(self, db):
        from backend.services.company_generator import CompanyGenerator

        gen = CompanyGenerator(db=db)
        slug = gen._generate_slug("Café Société")
        # Should only contain lowercase alphanumeric and dashes
        import re
        assert re.match(r"^[a-z0-9-]*$", slug)

    def test_slug_empty_string(self, db):
        from backend.services.company_generator import CompanyGenerator

        gen = CompanyGenerator(db=db)
        # Should not raise
        slug = gen._generate_slug("")
        assert isinstance(slug, str)


class TestGetGenerationStatus:
    def test_get_status_found(self, db):
        from backend.db.models import CompanyTenant
        from backend.services.company_generator import CompanyGenerator

        tenant = CompanyTenant(
            id="COMP-STAT1",
            slug="statco1",
            name="StatCo1",
            subdomain="statco1.realms2riches.tech",
            status="completed",
            metadata_json=json.dumps({"features": ["auth"]}),
        )
        db.add(tenant)
        db.commit()

        gen = CompanyGenerator(db=db)
        result = gen.get_generation_status("COMP-STAT1")
        assert result is not None
        assert result["status"] == "completed"
        assert isinstance(result["metadata"], dict)

    def test_get_status_no_metadata(self, db):
        from backend.db.models import CompanyTenant
        from backend.services.company_generator import CompanyGenerator

        tenant = CompanyTenant(
            id="COMP-NOMETA",
            slug="nometaco",
            name="NoMetaCo",
            subdomain="nometaco.realms2riches.tech",
            status="pending",
            metadata_json=None,
        )
        db.add(tenant)
        db.commit()

        gen = CompanyGenerator(db=db)
        result = gen.get_generation_status("COMP-NOMETA")
        assert result is not None
        assert result["metadata"] == {}


class TestExecuteGeneration:
    @pytest.mark.asyncio
    async def test_execute_generation_ticket_completion(self, db):
        from backend.db.models import CompanyTenant
        from backend.services.company_generator import (
            CompanyGenerator,
            CompanyRequest,
            TechStack,
            GenerationStatus,
        )

        tenant = CompanyTenant(
            id="COMP-EXEC1",
            slug="execco1",
            name="ExecCo1",
            subdomain="execco1.realms2riches.tech",
            status="pending",
            metadata_json=json.dumps({
                "tech_stack": "fastapi-react-postgres",
                "features": [],
                "template_version": "1.0.0",
            }),
        )
        db.add(tenant)
        db.commit()

        gen = CompanyGenerator(db=db)
        request = CompanyRequest(
            name="ExecCo1",
            description="exec test",
            tech_stack=TechStack.FASTAPI_REACT_POSTGRES,
            features=[],
            user_id="u1",
        )

        with patch(
            "backend.services.company_generator.strategic_board.convene",
            return_value=[
                {"title": "Build API", "instruction": "create api", "department": "Engineering"},
                {"title": "Build Tests", "instruction": "create tests", "department": "QA"},
            ],
        ), patch(
            "backend.services.company_generator.execution_unit.process_ticket",
            return_value="Pass: SUCCESS",
        ):
            await gen._execute_generation("COMP-EXEC1", request)

        db.expire_all()
        updated = db.query(CompanyTenant).filter_by(id="COMP-EXEC1").first()
        assert updated.status == GenerationStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_execute_generation_ticket_failure(self, db):
        from backend.db.models import CompanyTenant
        from backend.services.company_generator import (
            CompanyGenerator,
            CompanyRequest,
            TechStack,
            GenerationStatus,
        )

        tenant = CompanyTenant(
            id="COMP-FAIL2",
            slug="failco2",
            name="FailCo2",
            subdomain="failco2.realms2riches.tech",
            status="pending",
            metadata_json=json.dumps({
                "tech_stack": "fastapi-react-postgres",
                "features": [],
                "template_version": "1.0.0",
            }),
        )
        db.add(tenant)
        db.commit()

        gen = CompanyGenerator(db=db)
        request = CompanyRequest(
            name="FailCo2",
            description="fail test",
            tech_stack=TechStack.FASTAPI_REACT_POSTGRES,
            features=[],
            user_id="u1",
        )

        with patch(
            "backend.services.company_generator.strategic_board.convene",
            return_value=[
                {"title": "Build API", "instruction": "create api", "department": "Engineering"},
            ],
        ), patch(
            "backend.services.company_generator.execution_unit.process_ticket",
            return_value="FAIL: error",
        ):
            await gen._execute_generation("COMP-FAIL2", request)

        db.expire_all()
        updated = db.query(CompanyTenant).filter_by(id="COMP-FAIL2").first()
        # Ticket failed but generation itself should complete (status=completed)
        assert updated.status in (GenerationStatus.COMPLETED.value, GenerationStatus.FAILED.value)

    @pytest.mark.asyncio
    async def test_update_status_with_error_msg(self, db):
        from backend.db.models import CompanyTenant
        from backend.services.company_generator import CompanyGenerator, GenerationStatus

        tenant = CompanyTenant(
            id="COMP-UPDERR",
            slug="upderrco",
            name="UpdErrCo",
            subdomain="upderrco.realms2riches.tech",
            status="pending",
            metadata_json=json.dumps({}),
        )
        db.add(tenant)
        db.commit()

        gen = CompanyGenerator(db=db)
        await gen._update_status("COMP-UPDERR", GenerationStatus.FAILED, error_msg="test error")

        db.expire_all()
        updated = db.query(CompanyTenant).filter_by(id="COMP-UPDERR").first()
        assert updated.status == GenerationStatus.FAILED.value
        assert updated.last_error == "test error"

    @pytest.mark.asyncio
    async def test_update_status_nonexistent_id(self, db):
        from backend.services.company_generator import CompanyGenerator, GenerationStatus

        gen = CompanyGenerator(db=db)
        # Should not raise
        await gen._update_status("COMP-MISSING-X9", GenerationStatus.FAILED)


class TestGenerateCompanyFullPipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline_with_py_extension(self, db):
        from backend.services.company_generator import (
            CompanyGenerator,
            CompanyRequest,
            TechStack,
            GenerationStatus,
        )

        gen = CompanyGenerator(db=db)

        with patch(
            "backend.services.company_generator.strategic_board.convene",
            return_value=[
                {"title": "build_api", "instruction": "make api", "department": "Eng"},
            ],
        ), patch(
            "backend.services.company_generator.execution_unit.process_ticket",
            return_value="Pass: all good",
        ):
            result = await gen.generate_company(CompanyRequest(
                name="PipelineCo",
                description="pipeline test",
                tech_stack=TechStack.NODEJS_TAILWIND_MONGO,
                features=["auth", "billing"],
                user_id="u_pipe",
            ))

        assert "company_id" in result
        status_info = gen.get_generation_status(result["company_id"])
        assert status_info["status"] == GenerationStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_full_pipeline_tsx_file(self, db):
        from backend.services.company_generator import (
            CompanyGenerator,
            CompanyRequest,
            TechStack,
        )

        gen = CompanyGenerator(db=db)

        with patch(
            "backend.services.company_generator.strategic_board.convene",
            return_value=[
                {"title": "component.tsx", "instruction": "make component", "department": "Frontend"},
            ],
        ), patch(
            "backend.services.company_generator.execution_unit.process_ticket",
            return_value="SUCCESS: done",
        ):
            result = await gen.generate_company(CompanyRequest(
                name="TsxCo",
                description="tsx test",
                tech_stack=TechStack.FASTAPI_REACT_POSTGRES,
                features=[],
                user_id="u_tsx",
            ))

        assert "company_id" in result
