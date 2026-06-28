"""
tests/test_tenants_core.py
============================
Comprehensive coverage for backend/core/tenants.py

Covers:
- TenantService.register (new, existing)
- TenantService.list_tenants
- TenantService.get (found, not found)
- TenantService.provision (success docker, vm+docker, fallback)
- TenantService._deploy_docker_fallback (success, already exists, docker unavailable, timeout)
- TenantService.refresh_status
- TenantService._to_dict
"""

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars00")
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars01")
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

import subprocess
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.base import Base
from backend.db.models import CompanyTenant


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def _make_service(db_session):
    """Create a TenantService with all infra mocked."""
    from backend.core.tenants import TenantService

    mock_deployer = MagicMock()
    mock_deployer.deploy_docker_box.return_value = {
        "status": "running",
        "container_id": "abc123",
        "box_url": "https://test.realms2riches.tech",
    }
    mock_deployer.box_status.return_value = {"status": "running"}

    with patch("backend.core.tenants.SessionLocal", return_value=db_session):
        svc = TenantService(db=db_session)
    svc.deployer = mock_deployer
    return svc


def _seed_tenant(db_session, tenant_id="TEN-001", slug="test-co", name="Test Co"):
    existing = db_session.query(CompanyTenant).filter_by(id=tenant_id).first()
    if existing:
        return existing
    tenant = CompanyTenant(
        id=tenant_id,
        slug=slug,
        name=name,
        subdomain=f"{slug}.realms2riches.tech",
        status="pending",
        box_url=f"https://{slug}.realms2riches.tech",
        created_at=datetime.utcnow(),
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant


# ---------------------------------------------------------------------------
# Tests: _slugify utility
# ---------------------------------------------------------------------------


class TestSlugify:
    def test_slugify_simple(self):
        from backend.orchestration.box_deployer import _slugify

        assert _slugify("Hello World") == "hello-world"

    def test_slugify_special_chars(self):
        from backend.orchestration.box_deployer import _slugify

        assert _slugify("Acme Corp!!!") == "acme-corp"

    def test_slugify_empty_becomes_uuid(self):
        from backend.orchestration.box_deployer import _slugify

        result = _slugify("   !!! ")
        assert result.startswith("tenant-") or len(result) > 0

    def test_slugify_long_name_truncated(self):
        from backend.orchestration.box_deployer import _slugify

        result = _slugify("a" * 100)
        assert len(result) <= 48


# ---------------------------------------------------------------------------
# Tests: TenantService.register
# ---------------------------------------------------------------------------


class TestTenantServiceRegister:
    def test_register_new_tenant(self, db_session):
        svc = _make_service(db_session)
        tenant = svc.register("New Company")
        assert tenant.slug is not None
        assert tenant.status == "pending"

    def test_register_existing_tenant_returns_same(self, db_session):
        svc = _make_service(db_session)
        t1 = svc.register("Duplicate Co")
        t2 = svc.register("Duplicate Co")
        assert t1.id == t2.id

    def test_register_with_explicit_slug(self, db_session):
        svc = _make_service(db_session)
        tenant = svc.register("X Corp", slug="custom-slug-001")
        assert tenant.slug == "custom-slug-001"

    def test_register_db_error_raises(self, db_session):
        svc = _make_service(db_session)
        with patch.object(svc.db, "add", side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                svc.register("Error Company Xyz123")


# ---------------------------------------------------------------------------
# Tests: TenantService.list_tenants
# ---------------------------------------------------------------------------


class TestTenantServiceListTenants:
    def test_list_tenants_returns_all(self, db_session):
        svc = _make_service(db_session)
        _seed_tenant(db_session, "TEN-L001", "list-tenant-001")
        _seed_tenant(db_session, "TEN-L002", "list-tenant-002")
        tenants = svc.list_tenants()
        ids = [t.id for t in tenants]
        assert "TEN-L001" in ids
        assert "TEN-L002" in ids

    def test_list_tenants_empty(self, db_session):
        svc = _make_service(db_session)
        # Just ensure it returns a list
        tenants = svc.list_tenants()
        assert isinstance(tenants, list)


# ---------------------------------------------------------------------------
# Tests: TenantService.get
# ---------------------------------------------------------------------------


class TestTenantServiceGet:
    def test_get_existing_tenant(self, db_session):
        svc = _make_service(db_session)
        _seed_tenant(db_session, "TEN-G001", "get-tenant-001")
        result = svc.get("TEN-G001")
        assert result is not None
        assert result.id == "TEN-G001"

    def test_get_nonexistent_tenant(self, db_session):
        svc = _make_service(db_session)
        result = svc.get("NONEXISTENT")
        assert result is None


# ---------------------------------------------------------------------------
# Tests: TenantService.provision
# ---------------------------------------------------------------------------


class TestTenantServiceProvision:
    def test_provision_success_docker(self, db_session):
        svc = _make_service(db_session)
        _seed_tenant(db_session, "TEN-P001", "prov-tenant-001")
        result = svc.provision("TEN-P001")
        assert result.status == "running"
        assert result.container_id == "abc123"

    def test_provision_tenant_not_found(self, db_session):
        svc = _make_service(db_session)
        with pytest.raises(ValueError, match="tenant not found"):
            svc.provision("NONEXISTENT")

    def test_provision_docker_fails_uses_fallback(self, db_session):
        svc = _make_service(db_session)
        _seed_tenant(db_session, "TEN-P002", "prov-tenant-002")
        svc.deployer.deploy_docker_box.side_effect = Exception("docker error")

        with patch.object(
            svc,
            "_deploy_docker_fallback",
            return_value={"status": "running", "container_id": "fb001", "box_url": "http://x"},
        ):
            result = svc.provision("TEN-P002")

        assert result.status == "running"

    def test_provision_docker_fails_status_failed(self, db_session):
        svc = _make_service(db_session)
        _seed_tenant(db_session, "TEN-P003", "prov-tenant-003")
        svc.deployer.deploy_docker_box.return_value = {
            "status": "failed",
            "error": "container crash",
        }
        result = svc.provision("TEN-P003")
        assert result.status == "failed"

    def test_provision_with_vm(self, db_session):
        svc = _make_service(db_session)
        _seed_tenant(db_session, "TEN-P004", "prov-tenant-004")
        svc.deployer.provision_hyperv_vm.return_value = {"vm_id": "vm001"}

        result = svc.provision("TEN-P004", use_vm=True)
        svc.deployer.provision_hyperv_vm.assert_called_once()
        assert result is not None

    def test_provision_exception_marks_failed(self, db_session):
        svc = _make_service(db_session)
        _seed_tenant(db_session, "TEN-P005", "prov-tenant-005")
        svc.deployer.deploy_docker_box.side_effect = Exception("unexpected")
        svc.deployer  # ensure it's set

        with patch.object(svc, "_deploy_docker_fallback", side_effect=Exception("fallback failed")):
            with pytest.raises(Exception):
                svc.provision("TEN-P005")

        tenant = svc.get("TEN-P005")
        assert tenant.status == "failed"


# ---------------------------------------------------------------------------
# Tests: TenantService._deploy_docker_fallback
# ---------------------------------------------------------------------------


class TestDeployDockerFallback:
    def test_fallback_docker_run_success(self, db_session):
        svc = _make_service(db_session)
        _seed_tenant(db_session, "TEN-DF001", "fallback-001")
        tenant = svc.get("TEN-DF001")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "container_id_abc123\n"

        with patch("subprocess.run", return_value=mock_result):
            result = svc._deploy_docker_fallback(tenant)

        assert result["status"] == "running"
        assert "container_id" in result

    def test_fallback_docker_start_existing(self, db_session):
        svc = _make_service(db_session)
        _seed_tenant(db_session, "TEN-DF002", "fallback-002")
        tenant = svc.get("TEN-DF002")

        run_fail = MagicMock(returncode=1, stderr="already exists")
        start_ok = MagicMock(returncode=0)
        inspect_ok = MagicMock(returncode=0, stdout="abc456\n")

        with patch("subprocess.run", side_effect=[run_fail, start_ok, inspect_ok]):
            result = svc._deploy_docker_fallback(tenant)

        assert result["status"] == "running"

    def test_fallback_docker_not_available(self, db_session):
        svc = _make_service(db_session)
        _seed_tenant(db_session, "TEN-DF003", "fallback-003")
        tenant = svc.get("TEN-DF003")

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = svc._deploy_docker_fallback(tenant)

        assert result["status"] == "failed"
        assert "Docker CLI" in result["error"]

    def test_fallback_docker_timeout(self, db_session):
        svc = _make_service(db_session)
        _seed_tenant(db_session, "TEN-DF004", "fallback-004")
        tenant = svc.get("TEN-DF004")

        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="docker", timeout=60)
        ):
            result = svc._deploy_docker_fallback(tenant)

        assert result["status"] == "failed"
        assert "timed out" in result["error"].lower()

    def test_fallback_both_run_and_start_fail(self, db_session):
        svc = _make_service(db_session)
        _seed_tenant(db_session, "TEN-DF005", "fallback-005")
        tenant = svc.get("TEN-DF005")

        run_fail = MagicMock(returncode=1, stderr="run failed")
        start_fail = MagicMock(returncode=1, stderr="start failed")

        with patch("subprocess.run", side_effect=[run_fail, start_fail]):
            result = svc._deploy_docker_fallback(tenant)

        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# Tests: TenantService.refresh_status
# ---------------------------------------------------------------------------


class TestTenantServiceRefreshStatus:
    def test_refresh_status_running(self, db_session):
        svc = _make_service(db_session)
        _seed_tenant(db_session, "TEN-R001", "refresh-001")
        svc.deployer.box_status.return_value = {"status": "running"}

        tenant = svc.refresh_status("TEN-R001")
        assert tenant.status == "running"

    def test_refresh_status_exited(self, db_session):
        svc = _make_service(db_session)
        _seed_tenant(db_session, "TEN-R002", "refresh-002")
        svc.deployer.box_status.return_value = {"status": "exited"}

        tenant = svc.refresh_status("TEN-R002")
        assert tenant.status == "failed"

    def test_refresh_status_dead(self, db_session):
        svc = _make_service(db_session)
        _seed_tenant(db_session, "TEN-R003", "refresh-003")
        svc.deployer.box_status.return_value = {"status": "dead"}

        tenant = svc.refresh_status("TEN-R003")
        assert tenant.status == "failed"

    def test_refresh_status_not_found(self, db_session):
        svc = _make_service(db_session)
        result = svc.refresh_status("NONEXISTENT")
        assert result is None

    def test_refresh_status_unknown_state(self, db_session):
        svc = _make_service(db_session)
        _seed_tenant(db_session, "TEN-R004", "refresh-004")
        svc.deployer.box_status.return_value = {"status": "paused"}

        tenant = svc.refresh_status("TEN-R004")
        assert tenant is not None  # no status change for unknown states


# ---------------------------------------------------------------------------
# Tests: TenantService._to_dict
# ---------------------------------------------------------------------------


class TestTenantToDict:
    def test_to_dict_with_tenant(self, db_session):
        svc = _make_service(db_session)
        tenant = _seed_tenant(db_session, "TEN-D001", "dict-001")
        result = svc._to_dict(tenant)
        assert result is not None
        assert result["id"] == "TEN-D001"
        assert "status" in result

    def test_to_dict_with_none(self, db_session):
        svc = _make_service(db_session)
        result = svc._to_dict(None)
        assert result is None
