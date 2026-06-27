"""
tests/test_deployment_service_full.py
=======================================
Comprehensive coverage for backend/services/deployment_service.py

Covers service-layer logic: provisioning workflows, status transitions,
rollback logic, error propagation. All external infrastructure calls mocked.
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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.base import Base


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
    """Create a DeploymentService with all infra mocked."""
    from backend.services.deployment_service import DeploymentService

    mock_vm = MagicMock()
    mock_vm.provision_vm = AsyncMock()
    mock_vm.start_vm = AsyncMock()
    mock_vm._start_vm = AsyncMock()
    mock_vm.stop_vm = AsyncMock()
    mock_vm.restart_vm = AsyncMock()
    mock_vm.delete_vm = AsyncMock()
    mock_vm.get_vm_info = AsyncMock(return_value=MagicMock(state="running", uptime_seconds=3600))
    mock_vm.create_snapshot = AsyncMock()
    mock_vm.restore_snapshot = AsyncMock()

    mock_fm = MagicMock()

    with patch("backend.db.session.SessionLocal", return_value=db_session):
        svc = DeploymentService(vm_provisioner=mock_vm, file_manager=mock_fm)

    svc.db = db_session
    return svc, mock_vm


def _fake_deployment(dep_id="dep-001", company_id="comp-001", status="running"):
    return {
        "id": dep_id,
        "company_id": company_id,
        "tenant_name": "testco",
        "subdomain": "testco",
        "vm_name": "tenant-testco",
        "status": status,
        "url": "https://testco.realms2riches.tech",
        "ip_address": "10.0.0.1",
        "health_status": "healthy",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Tests: Utility parsers
# ---------------------------------------------------------------------------


class TestParsers:
    def test_parse_bytes_to_mbps_kb(self):
        from backend.services.deployment_service import _parse_bytes_to_mbps

        assert _parse_bytes_to_mbps("1024kB") == 1

    def test_parse_bytes_to_mbps_mb(self):
        from backend.services.deployment_service import _parse_bytes_to_mbps

        assert _parse_bytes_to_mbps("10MB") == 10

    def test_parse_bytes_to_mbps_gb(self):
        from backend.services.deployment_service import _parse_bytes_to_mbps

        assert _parse_bytes_to_mbps("1GB") >= 1000

    def test_parse_bytes_to_mbps_unknown(self):
        from backend.services.deployment_service import _parse_bytes_to_mbps

        assert _parse_bytes_to_mbps("unknown") == 0

    def test_parse_bytes_to_iops(self):
        from backend.services.deployment_service import _parse_bytes_to_iops

        assert isinstance(_parse_bytes_to_iops("100kB"), int)

    def test_parse_bytes_to_iops_unknown(self):
        from backend.services.deployment_service import _parse_bytes_to_iops

        assert _parse_bytes_to_iops("bad_value") == 0


# ---------------------------------------------------------------------------
# Tests: create_deployment
# ---------------------------------------------------------------------------


class TestCreateDeployment:
    @pytest.mark.asyncio
    async def test_create_deployment_returns_pending(self, db_session):
        from backend.services.deployment_service import DeploymentConfig

        svc, _ = _make_service(db_session)
        config = DeploymentConfig(
            company_id="comp-new",
            tenant_name="newco",
            subdomain="newco",
        )
        with patch.object(svc, "_execute_deployment", new_callable=AsyncMock):
            result = await svc.create_deployment(config)

        assert result["status"] == "pending"
        assert result["company_id"] == "comp-new"
        assert "id" in result

    @pytest.mark.asyncio
    async def test_create_deployment_db_save(self, db_session):
        from backend.services.deployment_service import DeploymentConfig

        svc, _ = _make_service(db_session)
        config = DeploymentConfig(
            company_id="comp-db",
            tenant_name="dbco",
            subdomain="dbco",
        )
        with patch.object(svc, "_execute_deployment", new_callable=AsyncMock):
            result = await svc.create_deployment(config)

        assert result["id"] in svc.deployments


# ---------------------------------------------------------------------------
# Tests: get_deployment
# ---------------------------------------------------------------------------


class TestGetDeployment:
    @pytest.mark.asyncio
    async def test_get_existing_deployment(self, db_session):
        svc, mock_vm = _make_service(db_session)
        dep = _fake_deployment("dep-get-001", status="running")
        svc.deployments["dep-get-001"] = dep

        result = await svc.get_deployment("dep-get-001")
        assert result["id"] == "dep-get-001"

    @pytest.mark.asyncio
    async def test_get_deployment_not_found(self, db_session):
        svc, _ = _make_service(db_session)
        with pytest.raises(ValueError, match="Deployment not found"):
            await svc.get_deployment("nonexistent")

    @pytest.mark.asyncio
    async def test_get_deployment_running_gets_vm_info(self, db_session):
        svc, mock_vm = _make_service(db_session)
        dep = _fake_deployment("dep-vm-001", status="running")
        svc.deployments["dep-vm-001"] = dep

        result = await svc.get_deployment("dep-vm-001")
        assert result["id"] == "dep-vm-001"
        mock_vm.get_vm_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_deployment_vm_info_error_handled(self, db_session):
        svc, mock_vm = _make_service(db_session)
        dep = _fake_deployment("dep-vm-err", status="running")
        svc.deployments["dep-vm-err"] = dep
        mock_vm.get_vm_info.side_effect = Exception("VM unreachable")

        result = await svc.get_deployment("dep-vm-err")
        assert result["id"] == "dep-vm-err"


# ---------------------------------------------------------------------------
# Tests: list_deployments
# ---------------------------------------------------------------------------


class TestListDeployments:
    @pytest.mark.asyncio
    async def test_list_all_deployments(self, db_session):
        svc, _ = _make_service(db_session)
        svc.deployments["ld-001"] = _fake_deployment("ld-001", status="running")
        svc.deployments["ld-002"] = _fake_deployment("ld-002", status="stopped")

        result = await svc.list_deployments()
        ids = [d["id"] for d in result]
        assert "ld-001" in ids
        assert "ld-002" in ids

    @pytest.mark.asyncio
    async def test_list_deployments_filtered_by_status(self, db_session):
        from backend.services.deployment_service import DeploymentStatus

        svc, _ = _make_service(db_session)
        svc.deployments["lf-001"] = _fake_deployment("lf-001", status="running")
        svc.deployments["lf-002"] = _fake_deployment("lf-002", status="stopped")

        result = await svc.list_deployments(status=DeploymentStatus.RUNNING)
        assert all(d["status"] == "running" for d in result)


# ---------------------------------------------------------------------------
# Tests: start_deployment
# ---------------------------------------------------------------------------


class TestStartDeployment:
    @pytest.mark.asyncio
    async def test_start_stopped_deployment(self, db_session):
        svc, mock_vm = _make_service(db_session)
        dep = _fake_deployment("dep-start", status="stopped")
        svc.deployments["dep-start"] = dep

        with patch.object(svc, "_verify_deployment", new_callable=AsyncMock):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await svc.start_deployment("dep-start")

        assert result["status"] == "running"
        mock_vm._start_vm.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_deployment_not_found(self, db_session):
        svc, _ = _make_service(db_session)
        with pytest.raises(ValueError, match="not found"):
            await svc.start_deployment("missing")

    @pytest.mark.asyncio
    async def test_start_deployment_not_stopped(self, db_session):
        svc, _ = _make_service(db_session)
        dep = _fake_deployment("dep-running", status="running")
        svc.deployments["dep-running"] = dep

        with pytest.raises(ValueError, match="not stopped"):
            await svc.start_deployment("dep-running")


# ---------------------------------------------------------------------------
# Tests: stop_deployment
# ---------------------------------------------------------------------------


class TestStopDeployment:
    @pytest.mark.asyncio
    async def test_stop_running_deployment(self, db_session):
        svc, mock_vm = _make_service(db_session)
        dep = _fake_deployment("dep-stop", status="running")
        svc.deployments["dep-stop"] = dep

        result = await svc.stop_deployment("dep-stop")
        assert result["status"] == "stopped"
        mock_vm.stop_vm.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_with_force(self, db_session):
        svc, mock_vm = _make_service(db_session)
        dep = _fake_deployment("dep-force-stop", status="running")
        svc.deployments["dep-force-stop"] = dep

        result = await svc.stop_deployment("dep-force-stop", force=True)
        assert result["status"] == "stopped"
        mock_vm.stop_vm.assert_called_once_with("tenant-testco", force=True)

    @pytest.mark.asyncio
    async def test_stop_deployment_not_found(self, db_session):
        svc, _ = _make_service(db_session)
        with pytest.raises(ValueError, match="not found"):
            await svc.stop_deployment("missing")

    @pytest.mark.asyncio
    async def test_stop_deployment_not_running(self, db_session):
        svc, _ = _make_service(db_session)
        dep = _fake_deployment("dep-stopped", status="stopped")
        svc.deployments["dep-stopped"] = dep

        with pytest.raises(ValueError, match="not running"):
            await svc.stop_deployment("dep-stopped")


# ---------------------------------------------------------------------------
# Tests: restart_deployment
# ---------------------------------------------------------------------------


class TestRestartDeployment:
    @pytest.mark.asyncio
    async def test_restart_deployment(self, db_session):
        svc, mock_vm = _make_service(db_session)
        dep = _fake_deployment("dep-restart", status="running")
        svc.deployments["dep-restart"] = dep

        with patch.object(svc, "_verify_deployment", new_callable=AsyncMock):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await svc.restart_deployment("dep-restart")

        assert result["status"] == "running"
        mock_vm.restart_vm.assert_called_once()

    @pytest.mark.asyncio
    async def test_restart_deployment_not_found(self, db_session):
        svc, _ = _make_service(db_session)
        with pytest.raises(ValueError, match="not found"):
            await svc.restart_deployment("missing")


# ---------------------------------------------------------------------------
# Tests: delete_deployment
# ---------------------------------------------------------------------------


class TestDeleteDeployment:
    @pytest.mark.asyncio
    async def test_delete_stopped_deployment(self, db_session):
        svc, mock_vm = _make_service(db_session)
        dep = _fake_deployment("dep-del", status="stopped")
        svc.deployments["dep-del"] = dep

        with patch.object(svc, "_remove_dns", new_callable=AsyncMock):
            await svc.delete_deployment("dep-del")

        assert svc.deployments["dep-del"]["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_delete_running_stops_first(self, db_session):
        svc, mock_vm = _make_service(db_session)
        dep = _fake_deployment("dep-del-run", status="running")
        svc.deployments["dep-del-run"] = dep

        with patch.object(svc, "_remove_dns", new_callable=AsyncMock):
            with patch.object(svc, "stop_deployment", new_callable=AsyncMock) as mock_stop:
                mock_stop.return_value = dep
                await svc.delete_deployment("dep-del-run")

        mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_without_vm(self, db_session):
        svc, mock_vm = _make_service(db_session)
        dep = _fake_deployment("dep-no-vm", status="stopped")
        svc.deployments["dep-no-vm"] = dep

        with patch.object(svc, "_remove_dns", new_callable=AsyncMock):
            await svc.delete_deployment("dep-no-vm", delete_vm=False)

        mock_vm.delete_vm.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, db_session):
        svc, _ = _make_service(db_session)
        with pytest.raises(ValueError, match="not found"):
            await svc.delete_deployment("missing")


# ---------------------------------------------------------------------------
# Tests: get_deployment_metrics
# ---------------------------------------------------------------------------


class TestGetDeploymentMetrics:
    @pytest.mark.asyncio
    async def test_metrics_non_running(self, db_session):
        svc, _ = _make_service(db_session)
        dep = _fake_deployment("dep-met-stopped", status="stopped")
        svc.deployments["dep-met-stopped"] = dep

        result = await svc.get_deployment_metrics("dep-met-stopped")
        assert result["cpu_usage_percent"] == 0

    @pytest.mark.asyncio
    async def test_metrics_running_docker_success(self, db_session):
        svc, _ = _make_service(db_session)
        dep = _fake_deployment("dep-met-run", status="running")
        svc.deployments["dep-met-run"] = dep

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "3.5%\t256MiB / 4GiB\t1.2kB / 3.4kB\t10MB / 5MB"

        with patch("subprocess.run", return_value=mock_result):
            result = await svc.get_deployment_metrics("dep-met-run")

        assert result["cpu_usage_percent"] == 3
        assert result["memory_usage_mb"] == 256

    @pytest.mark.asyncio
    async def test_metrics_running_docker_gib_memory(self, db_session):
        svc, _ = _make_service(db_session)
        dep = _fake_deployment("dep-met-gib", status="running")
        svc.deployments["dep-met-gib"] = dep

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "5.0%\t2GiB / 4GiB\t1.2kB / 3.4kB\t10MB / 5MB"

        with patch("subprocess.run", return_value=mock_result):
            result = await svc.get_deployment_metrics("dep-met-gib")

        assert result["memory_usage_mb"] == 2048

    @pytest.mark.asyncio
    async def test_metrics_running_docker_no_output(self, db_session):
        svc, _ = _make_service(db_session)
        dep = _fake_deployment("dep-met-no-out", status="running")
        svc.deployments["dep-met-no-out"] = dep

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            result = await svc.get_deployment_metrics("dep-met-no-out")

        assert result["cpu_usage_percent"] == 0

    @pytest.mark.asyncio
    async def test_metrics_docker_not_available(self, db_session):
        svc, _ = _make_service(db_session)
        dep = _fake_deployment("dep-met-nodk", status="running")
        svc.deployments["dep-met-nodk"] = dep

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = await svc.get_deployment_metrics("dep-met-nodk")

        assert result["cpu_usage_percent"] == 0

    @pytest.mark.asyncio
    async def test_metrics_docker_timeout(self, db_session):
        svc, _ = _make_service(db_session)
        dep = _fake_deployment("dep-met-to", status="running")
        svc.deployments["dep-met-to"] = dep

        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="docker", timeout=15),
        ):
            result = await svc.get_deployment_metrics("dep-met-to")

        assert result["cpu_usage_percent"] == 0

    @pytest.mark.asyncio
    async def test_metrics_not_found(self, db_session):
        svc, _ = _make_service(db_session)
        with pytest.raises(ValueError, match="not found"):
            await svc.get_deployment_metrics("missing")


# ---------------------------------------------------------------------------
# Tests: create_backup
# ---------------------------------------------------------------------------


class TestCreateBackup:
    @pytest.mark.asyncio
    async def test_backup_docker_success(self, db_session):
        svc, _ = _make_service(db_session)
        dep = _fake_deployment("dep-bak", status="running")
        svc.deployments["dep-bak"] = dep

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "sha256:abc123"

        with patch("subprocess.run", return_value=mock_result):
            result = await svc.create_backup("dep-bak")

        assert result["deployment_id"] == "dep-bak"
        assert "snapshot_name" in result

    @pytest.mark.asyncio
    async def test_backup_docker_fails(self, db_session):
        svc, _ = _make_service(db_session)
        dep = _fake_deployment("dep-bak-fail", status="running")
        svc.deployments["dep-bak-fail"] = dep

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "no such container"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="docker commit failed"):
                await svc.create_backup("dep-bak-fail")

    @pytest.mark.asyncio
    async def test_backup_docker_not_available(self, db_session):
        svc, mock_vm = _make_service(db_session)
        dep = _fake_deployment("dep-bak-vm", status="running")
        svc.deployments["dep-bak-vm"] = dep

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = await svc.create_backup("dep-bak-vm")

        mock_vm.create_snapshot.assert_called_once()
        assert result["deployment_id"] == "dep-bak-vm"

    @pytest.mark.asyncio
    async def test_backup_not_found(self, db_session):
        svc, _ = _make_service(db_session)
        with pytest.raises(ValueError, match="not found"):
            await svc.create_backup("missing")


# ---------------------------------------------------------------------------
# Tests: restore_backup
# ---------------------------------------------------------------------------


class TestRestoreBackup:
    @pytest.mark.asyncio
    async def test_restore_docker_success(self, db_session):
        svc, _ = _make_service(db_session)
        dep = _fake_deployment("dep-rst", status="stopped")
        svc.deployments["dep-rst"] = dep

        rm_result = MagicMock()
        rm_result.returncode = 0
        run_result = MagicMock()
        run_result.returncode = 0

        with patch("subprocess.run", side_effect=[rm_result, run_result]):
            result = await svc.restore_backup("dep-rst", "snap-20240101")

        assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_restore_docker_run_fails(self, db_session):
        svc, _ = _make_service(db_session)
        dep = _fake_deployment("dep-rst-fail", status="stopped")
        svc.deployments["dep-rst-fail"] = dep

        rm_result = MagicMock()
        rm_result.returncode = 0
        run_result = MagicMock()
        run_result.returncode = 1
        run_result.stderr = "image not found"

        with patch("subprocess.run", side_effect=[rm_result, run_result]):
            with pytest.raises(RuntimeError, match="Failed to restore"):
                await svc.restore_backup("dep-rst-fail", "snap-old")

    @pytest.mark.asyncio
    async def test_restore_docker_not_available(self, db_session):
        svc, mock_vm = _make_service(db_session)
        dep = _fake_deployment("dep-rst-nodk", status="running")
        svc.deployments["dep-rst-nodk"] = dep

        with (
            patch("subprocess.run", side_effect=FileNotFoundError),
            patch.object(svc, "stop_deployment", new_callable=AsyncMock, return_value=dep),
            patch.object(svc, "start_deployment", new_callable=AsyncMock, return_value=dep),
        ):
            result = await svc.restore_backup("dep-rst-nodk", "snap-vm")

        mock_vm.restore_snapshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_restore_not_found(self, db_session):
        svc, _ = _make_service(db_session)
        with pytest.raises(ValueError, match="not found"):
            await svc.restore_backup("missing", "snap")


# ---------------------------------------------------------------------------
# Tests: DB helpers
# ---------------------------------------------------------------------------


class TestDbHelpers:
    def test_save_and_get_deployment(self, db_session):
        svc, _ = _make_service(db_session)
        dep = _fake_deployment("db-dep-001")
        svc._save_deployment_to_db(dep)

        result = svc._get_deployment_from_db("db-dep-001")
        assert result is not None
        assert result["id"] == "db-dep-001"

    def test_save_deployment_updates_existing(self, db_session):
        svc, _ = _make_service(db_session)
        dep = _fake_deployment("db-dep-002", status="pending")
        svc._save_deployment_to_db(dep)

        dep["status"] = "running"
        svc._save_deployment_to_db(dep)

        result = svc._get_deployment_from_db("db-dep-002")
        assert result["status"] == "running"

    def test_get_deployment_not_in_db(self, db_session):
        svc, _ = _make_service(db_session)
        result = svc._get_deployment_from_db("nope")
        assert result is None

    def test_list_deployments_from_db(self, db_session):
        svc, _ = _make_service(db_session)
        dep = _fake_deployment("db-dep-list-001")
        svc._save_deployment_to_db(dep)

        result = svc._list_deployments_from_db()
        ids = [d["id"] for d in result]
        assert "db-dep-list-001" in ids

    def test_list_deployments_from_db_with_status(self, db_session):
        svc, _ = _make_service(db_session)
        dep = _fake_deployment("db-dep-list-002", status="stopped")
        svc._save_deployment_to_db(dep)

        result = svc._list_deployments_from_db(status="stopped")
        assert all(d["status"] == "stopped" for d in result)
