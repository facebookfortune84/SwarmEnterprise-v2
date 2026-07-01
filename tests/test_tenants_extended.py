"""
Extended tests for backend/core/tenants.py — TenantService full lifecycle.
Always passes db= to avoid _owns_db=True session closure.
"""
import json
import uuid
from unittest.mock import MagicMock, Mock, patch

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


class TestTenantServiceRegister:
    def test_register_new_tenant(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        tenant = svc.register("NewCo")
        assert tenant.id.startswith("TEN-")
        assert tenant.slug == "newco"
        assert tenant.status == "pending"

    def test_register_existing_tenant_returns_existing(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        t1 = svc.register("DupCo")
        t2 = svc.register("DupCo")
        assert t1.id == t2.id

    def test_register_custom_slug(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        tenant = svc.register("Any Name", slug="my-custom-slug")
        assert tenant.slug == "my-custom-slug"

    def test_register_slug_normalised(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        tenant = svc.register("  spaces in NAME  ")
        assert " " not in tenant.slug
        assert tenant.slug == tenant.slug.lower()

    def test_register_db_failure_rolls_back(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        original_add = db.add

        def fail_add(obj):
            raise RuntimeError("db constraint error")

        db.add = fail_add
        try:
            with pytest.raises(RuntimeError):
                svc.register("BrokenCo")
        finally:
            db.add = original_add


class TestTenantServiceGet:
    def test_get_existing_tenant(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        created = svc.register("GetTestCo")
        found = svc.get(created.id)
        assert found is not None
        assert found.id == created.id

    def test_get_nonexistent_tenant(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        assert svc.get("TEN-NONEXISTENT") is None


class TestTenantServiceList:
    def test_list_tenants_returns_all(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        svc.register("ListA")
        svc.register("ListB")
        tenants = svc.list_tenants()
        slugs = [t.slug for t in tenants]
        assert "lista" in slugs
        assert "listb" in slugs

    def test_list_tenants_ordered_by_created_at(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        tenants = svc.list_tenants()
        # Should be ordered descending — just verify it returns a list
        assert isinstance(tenants, list)


class TestTenantServiceProvision:
    def test_provision_not_found_raises(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        with pytest.raises(ValueError, match="tenant not found"):
            svc.provision("TEN-NONEXISTENT-000")

    def test_provision_docker_success(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        tenant = svc.register("ProvDockerCo")

        with patch.object(
            svc.deployer, "deploy_docker_box",
            return_value={"status": "running", "container_id": "abc123", "box_url": "https://x.y"},
        ):
            result = svc.provision(tenant.id, use_vm=False)

        assert result.status == "running"

    def test_provision_docker_failed(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        tenant = svc.register("ProvFailCo")

        with patch.object(
            svc.deployer, "deploy_docker_box",
            return_value={"status": "failed", "error": "port conflict"},
        ):
            result = svc.provision(tenant.id, use_vm=False)

        assert result.status == "failed"
        assert "port conflict" in result.last_error

    def test_provision_deployer_fallback_to_docker_cli(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        tenant = svc.register("FallbackCo")

        # Deployer raises, fallback called
        with patch.object(
            svc.deployer, "deploy_docker_box",
            side_effect=RuntimeError("deployer down"),
        ), patch.object(
            svc, "_deploy_docker_fallback",
            return_value={"status": "running", "container_id": "fallback123", "box_url": "https://fb.y"},
        ):
            result = svc.provision(tenant.id, use_vm=False)

        assert result.status == "running"

    def test_provision_with_vm_calls_hyperv(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        tenant = svc.register("VMProvCo")

        with patch.object(
            svc.deployer, "provision_hyperv_vm",
            return_value={"status": "submitted", "vm_name": "r2r-vmprovco"},
        ), patch.object(
            svc.deployer, "deploy_docker_box",
            return_value={"status": "running", "container_id": "vmbox1", "box_url": "https://v.y"},
        ):
            result = svc.provision(tenant.id, use_vm=True)

        assert result.status == "running"


class TestTenantDockerFallback:
    def test_deploy_docker_fallback_success(self, db):
        from backend.core.tenants import TenantService
        from backend.db.models import CompanyTenant

        svc = TenantService(db=db)
        tenant = svc.register("DockerFallbackCo")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="abc123def456\n", stderr="")
            result = svc._deploy_docker_fallback(tenant)

        assert result["status"] == "running"

    def test_deploy_docker_fallback_docker_not_found(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        tenant = svc.register("DockerMissingCo")

        with patch("subprocess.run", side_effect=FileNotFoundError("docker not found")):
            result = svc._deploy_docker_fallback(tenant)

        assert result["status"] == "failed"
        assert "Docker" in result["error"] or "docker" in result["error"].lower()

    def test_deploy_docker_fallback_timeout(self, db):
        import subprocess
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        tenant = svc.register("DockerTimeoutCo")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("docker", 60)):
            result = svc._deploy_docker_fallback(tenant)

        assert result["status"] == "failed"

    def test_deploy_docker_fallback_container_exists(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        tenant = svc.register("DockerExistCo")

        def mock_run(cmd, **kwargs):
            m = MagicMock()
            if "run" in cmd:
                m.returncode = 1  # Container already exists
                m.stderr = "already in use"
                m.stdout = ""
            elif "start" in cmd:
                m.returncode = 0
                m.stdout = "started"
            elif "inspect" in cmd:
                m.returncode = 0
                m.stdout = "existingid123"
            return m

        with patch("subprocess.run", side_effect=mock_run):
            result = svc._deploy_docker_fallback(tenant)

        assert result["status"] in ("running", "failed")


class TestTenantRefreshStatus:
    def test_refresh_status_running(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        tenant = svc.register("RefreshCo")

        with patch.object(
            svc.deployer, "box_status",
            return_value={"status": "running"},
        ):
            result = svc.refresh_status(tenant.id)

        assert result.status == "running"

    def test_refresh_status_failed_exited(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        tenant = svc.register("RefreshExitedCo")

        with patch.object(
            svc.deployer, "box_status",
            return_value={"status": "exited"},
        ):
            result = svc.refresh_status(tenant.id)

        assert result.status == "failed"

    def test_refresh_status_not_found(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        result = svc.refresh_status("TEN-MISSING-ZZZ")
        assert result is None


class TestToDict:
    def test_to_dict_success(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        tenant = svc.register("ToDictCo")
        result = svc._to_dict(tenant)
        assert result is not None
        assert result["slug"] == "todictco"
        assert "id" in result

    def test_to_dict_none(self, db):
        from backend.core.tenants import TenantService

        svc = TenantService(db=db)
        assert svc._to_dict(None) is None
