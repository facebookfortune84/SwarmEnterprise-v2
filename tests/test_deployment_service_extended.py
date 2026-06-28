"""
Extended tests for backend/services/deployment_service.py
Covers DeploymentService methods with all external calls mocked.
"""
import subprocess
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.base import Base
from backend.services.deployment_service import (
    DeploymentService,
    DeploymentConfig,
    DeploymentStatus,
    _parse_bytes_to_mbps,
    _parse_bytes_to_iops,
)


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


def _make_service(db_session: Session) -> DeploymentService:
    """Create a DeploymentService with mocked VM provisioner and file manager."""
    mock_vm = AsyncMock()
    mock_fm = MagicMock()
    mock_fm.retrieve_company.return_value = None
    mock_fm.company_exists.return_value = False

    svc = DeploymentService.__new__(DeploymentService)
    svc.vm_provisioner = mock_vm
    svc.file_manager = mock_fm
    svc.db = db_session
    svc.deployments = {}
    return svc


def _base_deployment(dep_id: str = "deploy-c1", status: str = "running") -> dict:
    return {
        "id": dep_id,
        "company_id": "c1",
        "tenant_name": "tenant1",
        "subdomain": "tenant1",
        "vm_name": "tenant-tenant1",
        "status": status,
        "url": "https://tenant1.realms2riches.tech",
        "ip_address": "10.0.0.1",
        "health_status": "healthy",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


class TestParseHelpers:
    def test_parse_mbps_gb(self):
        assert _parse_bytes_to_mbps("1.5GB") == 1500

    def test_parse_mbps_mb(self):
        assert _parse_bytes_to_mbps("2.0MB") == 2

    def test_parse_mbps_kb(self):
        assert _parse_bytes_to_mbps("500kB") == 0  # rounded down

    def test_parse_mbps_invalid(self):
        assert _parse_bytes_to_mbps("not-a-number") == 0

    def test_parse_iops_delegates(self):
        assert _parse_bytes_to_iops("1.0MB") == _parse_bytes_to_mbps("1.0MB")


class TestCreateDeployment:
    @pytest.mark.asyncio
    async def test_create_deployment_success(self, db):
        svc = _make_service(db)

        with patch("backend.services.deployment_service.asyncio.create_task"):
            config = DeploymentConfig(
                company_id="c1",
                tenant_name="tenant1",
                subdomain="tenant1",
            )
            deployment = await svc.create_deployment(config)

        assert deployment["id"] == "deploy-c1"
        assert deployment["status"] == DeploymentStatus.PENDING

    @pytest.mark.asyncio
    async def test_create_deployment_stores_in_memory(self, db):
        svc = _make_service(db)

        with patch("backend.services.deployment_service.asyncio.create_task"):
            config = DeploymentConfig(company_id="c2", tenant_name="t2", subdomain="t2")
            await svc.create_deployment(config)

        assert "deploy-c2" in svc.deployments


class TestGetDeployment:
    @pytest.mark.asyncio
    async def test_get_deployment_found(self, db):
        svc = _make_service(db)
        dep = _base_deployment()
        svc.deployments["deploy-c1"] = dep

        result = await svc.get_deployment("deploy-c1")
        assert result["id"] == "deploy-c1"

    @pytest.mark.asyncio
    async def test_get_deployment_not_found(self, db):
        svc = _make_service(db)

        with pytest.raises(ValueError, match="Deployment not found"):
            await svc.get_deployment("nonexistent")

    @pytest.mark.asyncio
    async def test_get_deployment_running_gets_vm_info(self, db):
        from backend.orchestration.vm_provisioner import VMInfo, VMState

        svc = _make_service(db)
        dep = _base_deployment(status="running")
        svc.deployments["deploy-c1"] = dep

        vm_info = VMInfo(
            name="tenant-tenant1",
            state=VMState.RUNNING,
            ip_address="10.0.0.1",
            memory_mb=4096,
            cpu_cores=2,
            disk_size_gb=50,
            created_at=datetime.utcnow().isoformat(),
            uptime_seconds=3600,
        )
        svc.vm_provisioner.get_vm_info = AsyncMock(return_value=vm_info)

        result = await svc.get_deployment("deploy-c1")
        assert result["vm_state"] == VMState.RUNNING


class TestListDeployments:
    @pytest.mark.asyncio
    async def test_list_deployments_all(self, db):
        svc = _make_service(db)
        svc.deployments["d1"] = _base_deployment("d1", "running")
        svc.deployments["d2"] = _base_deployment("d2", "stopped")

        result = await svc.list_deployments()
        assert len(result) >= 2

    @pytest.mark.asyncio
    async def test_list_deployments_filtered(self, db):
        svc = _make_service(db)
        svc.deployments["d1"] = _base_deployment("d1", "running")
        svc.deployments["d2"] = _base_deployment("d2", "stopped")

        result = await svc.list_deployments(status=DeploymentStatus.RUNNING)
        statuses = [d["status"] for d in result]
        assert all(s == DeploymentStatus.RUNNING for s in statuses)


class TestStartDeployment:
    @pytest.mark.asyncio
    async def test_start_not_found(self, db):
        svc = _make_service(db)

        with pytest.raises(ValueError, match="not found"):
            await svc.start_deployment("nonexistent")

    @pytest.mark.asyncio
    async def test_start_not_stopped(self, db):
        svc = _make_service(db)
        dep = _base_deployment(status="running")
        svc.deployments["deploy-c1"] = dep

        with pytest.raises(ValueError, match="not stopped"):
            await svc.start_deployment("deploy-c1")

    @pytest.mark.asyncio
    async def test_start_success(self, db):
        svc = _make_service(db)
        dep = _base_deployment(status="stopped")
        svc.deployments["deploy-c1"] = dep

        with patch.object(svc.vm_provisioner, "_start_vm", new_callable=AsyncMock), \
             patch("asyncio.sleep", new_callable=AsyncMock), \
             patch.object(svc, "_verify_deployment", new_callable=AsyncMock):
            result = await svc.start_deployment("deploy-c1")

        assert result["status"] == DeploymentStatus.RUNNING


class TestStopDeployment:
    @pytest.mark.asyncio
    async def test_stop_not_found(self, db):
        svc = _make_service(db)

        with pytest.raises(ValueError, match="not found"):
            await svc.stop_deployment("nonexistent")

    @pytest.mark.asyncio
    async def test_stop_not_running(self, db):
        svc = _make_service(db)
        dep = _base_deployment(status="stopped")
        svc.deployments["deploy-c1"] = dep

        with pytest.raises(ValueError, match="not running"):
            await svc.stop_deployment("deploy-c1")

    @pytest.mark.asyncio
    async def test_stop_success(self, db):
        svc = _make_service(db)
        dep = _base_deployment(status="running")
        svc.deployments["deploy-c1"] = dep

        svc.vm_provisioner.stop_vm = AsyncMock()

        result = await svc.stop_deployment("deploy-c1")
        assert result["status"] == DeploymentStatus.STOPPED

    @pytest.mark.asyncio
    async def test_stop_force(self, db):
        svc = _make_service(db)
        dep = _base_deployment(status="running")
        svc.deployments["deploy-c1"] = dep

        svc.vm_provisioner.stop_vm = AsyncMock()

        result = await svc.stop_deployment("deploy-c1", force=True)
        svc.vm_provisioner.stop_vm.assert_called_with("tenant-tenant1", force=True)
        assert result["status"] == DeploymentStatus.STOPPED


class TestRestartDeployment:
    @pytest.mark.asyncio
    async def test_restart_not_found(self, db):
        svc = _make_service(db)

        with pytest.raises(ValueError, match="not found"):
            await svc.restart_deployment("nonexistent")

    @pytest.mark.asyncio
    async def test_restart_success(self, db):
        svc = _make_service(db)
        dep = _base_deployment(status="running")
        svc.deployments["deploy-c1"] = dep

        with patch.object(svc.vm_provisioner, "restart_vm", new_callable=AsyncMock), \
             patch("asyncio.sleep", new_callable=AsyncMock), \
             patch.object(svc, "_verify_deployment", new_callable=AsyncMock):
            result = await svc.restart_deployment("deploy-c1")

        assert result["status"] == DeploymentStatus.RUNNING


class TestDeleteDeployment:
    @pytest.mark.asyncio
    async def test_delete_not_found(self, db):
        svc = _make_service(db)

        with pytest.raises(ValueError, match="not found"):
            await svc.delete_deployment("nonexistent")

    @pytest.mark.asyncio
    async def test_delete_stopped_deployment(self, db):
        svc = _make_service(db)
        dep = _base_deployment("deploy-del1", "stopped")
        svc.deployments["deploy-del1"] = dep

        svc.vm_provisioner.delete_vm = AsyncMock()
        with patch.object(svc, "_remove_dns", new_callable=AsyncMock):
            await svc.delete_deployment("deploy-del1")

        assert svc.deployments["deploy-del1"]["status"] == DeploymentStatus.DELETED

    @pytest.mark.asyncio
    async def test_delete_running_deployment_stops_first(self, db):
        svc = _make_service(db)
        dep = _base_deployment("deploy-del2", "running")
        svc.deployments["deploy-del2"] = dep

        svc.vm_provisioner.stop_vm = AsyncMock()
        svc.vm_provisioner.delete_vm = AsyncMock()
        with patch.object(svc, "_remove_dns", new_callable=AsyncMock):
            await svc.delete_deployment("deploy-del2")

        assert svc.deployments["deploy-del2"]["status"] == DeploymentStatus.DELETED

    @pytest.mark.asyncio
    async def test_delete_no_vm(self, db):
        svc = _make_service(db)
        dep = _base_deployment("deploy-del3", "stopped")
        svc.deployments["deploy-del3"] = dep

        with patch.object(svc, "_remove_dns", new_callable=AsyncMock):
            await svc.delete_deployment("deploy-del3", delete_vm=False)

        svc.vm_provisioner.delete_vm.assert_not_called()


class TestGetDeploymentMetrics:
    @pytest.mark.asyncio
    async def test_metrics_not_running_returns_zeros(self, db):
        svc = _make_service(db)
        dep = _base_deployment(status="stopped")
        svc.deployments["deploy-c1"] = dep

        metrics = await svc.get_deployment_metrics("deploy-c1")
        assert metrics["cpu_usage_percent"] == 0
        assert metrics["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_metrics_not_found(self, db):
        svc = _make_service(db)

        with pytest.raises(ValueError, match="not found"):
            await svc.get_deployment_metrics("nonexistent")

    @pytest.mark.asyncio
    async def test_metrics_docker_not_available(self, db):
        svc = _make_service(db)
        dep = _base_deployment(status="running")
        svc.deployments["deploy-c1"] = dep

        with patch("subprocess.run", side_effect=FileNotFoundError("no docker")):
            metrics = await svc.get_deployment_metrics("deploy-c1")

        assert metrics["cpu_usage_percent"] == 0

    @pytest.mark.asyncio
    async def test_metrics_docker_stats_parsed(self, db):
        svc = _make_service(db)
        dep = _base_deployment(status="running")
        svc.deployments["deploy-c1"] = dep

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "25%\t256MiB / 4GiB\t1.2MB / 3.4MB\t10MB / 5MB"

        with patch("subprocess.run", return_value=mock_result):
            metrics = await svc.get_deployment_metrics("deploy-c1")

        assert metrics["cpu_usage_percent"] == 25
        assert metrics["memory_usage_mb"] == 256


class TestCreateBackup:
    @pytest.mark.asyncio
    async def test_backup_not_found(self, db):
        svc = _make_service(db)

        with pytest.raises(ValueError, match="not found"):
            await svc.create_backup("nonexistent")

    @pytest.mark.asyncio
    async def test_backup_docker_success(self, db):
        svc = _make_service(db)
        dep = _base_deployment(status="running")
        svc.deployments["deploy-c1"] = dep

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            backup = await svc.create_backup("deploy-c1")

        assert "snapshot_name" in backup
        assert backup["deployment_id"] == "deploy-c1"

    @pytest.mark.asyncio
    async def test_backup_docker_not_found_uses_vm(self, db):
        svc = _make_service(db)
        dep = _base_deployment(status="running")
        svc.deployments["deploy-c1"] = dep

        svc.vm_provisioner.create_snapshot = AsyncMock()

        with patch("subprocess.run", side_effect=FileNotFoundError("no docker")):
            backup = await svc.create_backup("deploy-c1")

        assert "snapshot_name" in backup
        svc.vm_provisioner.create_snapshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_backup_docker_commit_fails(self, db):
        svc = _make_service(db)
        dep = _base_deployment(status="running")
        svc.deployments["deploy-c1"] = dep

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "permission denied"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="docker commit failed"):
                await svc.create_backup("deploy-c1")


class TestDeployApplication:
    @pytest.mark.asyncio
    async def test_deploy_docker_not_found_no_raise(self, db):
        """FileNotFoundError (no Docker CLI) is silently handled."""
        svc = _make_service(db)

        with patch("subprocess.run", side_effect=FileNotFoundError("no docker")):
            await svc._deploy_application("deploy-c1", DeploymentConfig(
                company_id="c1", tenant_name="tenant1", subdomain="tenant1"
            ))

    @pytest.mark.asyncio
    async def test_deploy_docker_timeout_raises(self, db):
        svc = _make_service(db)

        def mock_run(cmd, **kwargs):
            if "rm" in cmd:
                return MagicMock(returncode=0)
            raise subprocess.TimeoutExpired(cmd, 60)

        with patch("subprocess.run", side_effect=mock_run):
            with pytest.raises(RuntimeError, match="timed out"):
                await svc._deploy_application("deploy-c1", DeploymentConfig(
                    company_id="c1", tenant_name="tenant1", subdomain="tenant1"
                ))


class TestConfigureDNS:
    @pytest.mark.asyncio
    async def test_configure_dns_no_cloudflare_permission_error(self, db):
        """PermissionError on hosts file is silently logged."""
        svc = _make_service(db)
        svc.deployments["deploy-c1"] = _base_deployment()

        with patch.dict("os.environ", {"CLOUDFLARE_API_TOKEN": "", "CLOUDFLARE_ZONE_ID": ""}), \
             patch("builtins.open", side_effect=PermissionError("not writable")):
            # Should not raise
            await svc._configure_dns("deploy-c1", DeploymentConfig(
                company_id="c1", tenant_name="tenant1", subdomain="subdomain"
            ))


class TestSavingAndLoading:
    def test_save_and_get_deployment(self, db):
        svc = _make_service(db)
        dep = _base_deployment("deploy-save1")

        svc._save_deployment_to_db(dep)
        loaded = svc._get_deployment_from_db("deploy-save1")
        assert loaded is not None
        assert loaded["id"] == "deploy-save1"

    def test_list_from_db(self, db):
        svc = _make_service(db)
        dep1 = _base_deployment("deploy-lst1", "running")
        dep2 = _base_deployment("deploy-lst2", "stopped")
        svc._save_deployment_to_db(dep1)
        svc._save_deployment_to_db(dep2)

        all_deps = svc._list_deployments_from_db()
        ids = [d["id"] for d in all_deps]
        assert "deploy-lst1" in ids

    def test_list_from_db_filtered(self, db):
        svc = _make_service(db)
        dep = _base_deployment("deploy-flt1", "failed")
        svc._save_deployment_to_db(dep)

        failed = svc._list_deployments_from_db(status="failed")
        assert all(d["status"] == "failed" for d in failed)

    def test_get_nonexistent_returns_none(self, db):
        svc = _make_service(db)
        assert svc._get_deployment_from_db("nonexistent-xxx") is None
