"""
Unit tests for Deployment Service
"""
import pytest
from unittest.mock import patch
from backend.services.deployment_service import (
    DeploymentService,
    DeploymentConfig,
    DeploymentStatus,
)


class TestDeploymentService:
    """Test suite for DeploymentService"""

    @pytest.fixture
    def deployment_service(self):
        """Create a DeploymentService instance for testing"""
        return DeploymentService()

    @pytest.fixture
    def sample_config(self):
        """Sample deployment configuration"""
        return DeploymentConfig(
            company_id="comp-123",
            tenant_name="test-tenant",
            subdomain="test",
            memory_mb=4096,
            cpu_cores=2,
            disk_size_gb=50,
            auto_start=True,
            backup_enabled=True,
        )

    @pytest.mark.asyncio
    async def test_create_deployment(self, deployment_service, sample_config):
        """Test deployment creation"""
        deployment = await deployment_service.create_deployment(sample_config)

        assert deployment is not None
        assert "id" in deployment
        assert "company_id" in deployment
        assert "tenant_name" in deployment
        assert "subdomain" in deployment
        assert "vm_name" in deployment
        assert "status" in deployment
        assert "url" in deployment
        assert deployment["status"] == DeploymentStatus.PENDING
        assert deployment["company_id"] == sample_config.company_id
        assert deployment["tenant_name"] == sample_config.tenant_name
        assert deployment["subdomain"] == sample_config.subdomain

    @pytest.mark.asyncio
    async def test_create_deployment_generates_vm_name(self, deployment_service, sample_config):
        """Test that VM name is generated correctly"""
        deployment = await deployment_service.create_deployment(sample_config)

        assert deployment["vm_name"] == f"tenant-{sample_config.tenant_name}"

    @pytest.mark.asyncio
    async def test_create_deployment_generates_url(self, deployment_service, sample_config):
        """Test that deployment URL is generated correctly"""
        deployment = await deployment_service.create_deployment(sample_config)

        expected_url = f"https://{sample_config.subdomain}.realms2riches.tech"
        assert deployment["url"] == expected_url

    @pytest.mark.asyncio
    async def test_create_deployment_stores_record(self, deployment_service, sample_config):
        """Test that deployment is stored in database and in-memory cache"""
        deployment = await deployment_service.create_deployment(sample_config)
        deployment_id = deployment["id"]

        # Verify deployment was saved to in-memory cache
        assert deployment_id in deployment_service.deployments
        stored_deployment = deployment_service.deployments[deployment_id]
        assert stored_deployment["id"] == deployment_id

        # Verify deployment was also saved to database
        if deployment_service.db:
            from backend.db.models import Deployment

            db_deployment = (
                deployment_service.db.query(Deployment).filter_by(id=deployment_id).first()
            )
            assert db_deployment is not None
            assert db_deployment.id == deployment_id
            assert db_deployment.tenant_id == sample_config.company_id

    @pytest.mark.asyncio
    async def test_get_deployment_exists(self, deployment_service, sample_config):
        """Test getting existing deployment"""
        created = await deployment_service.create_deployment(sample_config)
        deployment_id = created["id"]

        # Wait a moment for async task to start
        import asyncio

        await asyncio.sleep(0.1)

        deployment = await deployment_service.get_deployment(deployment_id)

        assert deployment is not None
        assert deployment["id"] == deployment_id

    @pytest.mark.asyncio
    async def test_get_deployment_not_found(self, deployment_service):
        """Test getting non-existent deployment"""
        with pytest.raises(ValueError, match="Deployment not found"):
            await deployment_service.get_deployment("nonexistent")

    @pytest.mark.asyncio
    async def test_list_deployments_empty(self, deployment_service):
        """Test listing deployments when none exist"""
        deployments = await deployment_service.list_deployments()

        assert deployments is not None
        assert isinstance(deployments, list)
        assert len(deployments) == 0

    @pytest.mark.asyncio
    async def test_list_deployments_with_data(self, deployment_service, sample_config):
        """Test listing deployments with existing data"""
        await deployment_service.create_deployment(sample_config)

        deployments = await deployment_service.list_deployments()

        assert len(deployments) == 1
        assert deployments[0]["company_id"] == sample_config.company_id

    @pytest.mark.asyncio
    async def test_list_deployments_filter_by_status(self, deployment_service):
        """Test filtering deployments by status"""
        # Create deployments with different statuses
        config1 = DeploymentConfig(company_id="comp-1", tenant_name="tenant1", subdomain="sub1")
        config2 = DeploymentConfig(company_id="comp-2", tenant_name="tenant2", subdomain="sub2")

        deployment1 = await deployment_service.create_deployment(config1)
        deployment2 = await deployment_service.create_deployment(config2)

        # Manually set different statuses for testing
        deployment_service.deployments[deployment1["id"]]["status"] = DeploymentStatus.RUNNING
        deployment_service.deployments[deployment2["id"]]["status"] = DeploymentStatus.STOPPED

        running_deployments = await deployment_service.list_deployments(
            status=DeploymentStatus.RUNNING
        )

        assert len(running_deployments) == 1
        assert running_deployments[0]["status"] == DeploymentStatus.RUNNING

    @pytest.mark.asyncio
    async def test_stop_deployment(self, deployment_service):
        """Test stopping a running deployment"""
        config = DeploymentConfig(company_id="comp-123", tenant_name="test", subdomain="test")
        deployment = await deployment_service.create_deployment(config)
        deployment_id = deployment["id"]

        # Set to running first
        deployment_service.deployments[deployment_id]["status"] = DeploymentStatus.RUNNING

        # Mock the VM provisioner stop method
        async def mock_stop_vm(vm_name, force=False):
            pass

        deployment_service.vm_provisioner.stop_vm = mock_stop_vm

        stopped = await deployment_service.stop_deployment(deployment_id)

        assert stopped["status"] == DeploymentStatus.STOPPED
        assert stopped["health_status"] == "stopped"

    @pytest.mark.asyncio
    async def test_stop_deployment_not_running(self, deployment_service):
        """Test stopping a deployment that's not running"""
        config = DeploymentConfig(company_id="comp-123", tenant_name="test", subdomain="test")
        deployment = await deployment_service.create_deployment(config)
        deployment_id = deployment["id"]

        with pytest.raises(ValueError, match="not running"):
            await deployment_service.stop_deployment(deployment_id)

    @pytest.mark.asyncio
    async def test_start_deployment(self, deployment_service):
        """Test starting a stopped deployment"""
        config = DeploymentConfig(company_id="comp-123", tenant_name="test", subdomain="test")
        deployment = await deployment_service.create_deployment(config)
        deployment_id = deployment["id"]

        # Set to stopped
        deployment_service.deployments[deployment_id]["status"] = DeploymentStatus.STOPPED

        # Mock VM provisioner methods
        async def mock_start_vm(vm_name):
            pass

        deployment_service.vm_provisioner._start_vm = mock_start_vm

        # Mock verify deployment
        async def mock_verify(dep_id):
            pass

        deployment_service._verify_deployment = mock_verify

        started = await deployment_service.start_deployment(deployment_id)

        assert started["status"] == DeploymentStatus.RUNNING
        assert started["health_status"] == "healthy"

    @pytest.mark.asyncio
    async def test_restart_deployment(self, deployment_service):
        """Test restarting a deployment"""
        config = DeploymentConfig(company_id="comp-123", tenant_name="test", subdomain="test")
        deployment = await deployment_service.create_deployment(config)
        deployment_id = deployment["id"]

        # Set to running
        deployment_service.deployments[deployment_id]["status"] = DeploymentStatus.RUNNING

        # Mock VM provisioner methods
        async def mock_restart_vm(vm_name):
            pass

        deployment_service.vm_provisioner.restart_vm = mock_restart_vm

        # Mock verify deployment
        async def mock_verify(dep_id):
            pass

        deployment_service._verify_deployment = mock_verify

        restarted = await deployment_service.restart_deployment(deployment_id)

        assert restarted["status"] == DeploymentStatus.RUNNING
        assert restarted["health_status"] == "healthy"

    @pytest.mark.asyncio
    async def test_delete_deployment(self, deployment_service):
        """Test deleting a deployment"""
        config = DeploymentConfig(company_id="comp-123", tenant_name="test", subdomain="test")
        deployment = await deployment_service.create_deployment(config)
        deployment_id = deployment["id"]

        # Set to stopped
        deployment_service.deployments[deployment_id]["status"] = DeploymentStatus.STOPPED

        # Mock VM provisioner methods
        async def mock_delete_vm(vm_name, delete_disks=True):
            pass

        deployment_service.vm_provisioner.delete_vm = mock_delete_vm

        # Mock DNS removal
        async def mock_remove_dns(dep_id):
            pass

        deployment_service._remove_dns = mock_remove_dns

        await deployment_service.delete_deployment(deployment_id)

        assert deployment_service.deployments[deployment_id]["status"] == DeploymentStatus.DELETED

    @pytest.mark.asyncio
    async def test_create_backup(self, deployment_service):
        """Test creating a deployment backup"""
        # Pre-mock all VM/docker operations so no real subprocesses are spawned
        async def mock_provision_vm(config):
            return {"vm_name": config.tenant_name, "ip": "127.0.0.1", "status": "running"}

        async def mock_create_snapshot(vm_name, snapshot_name):
            pass

        deployment_service.vm_provisioner.provision_vm = mock_provision_vm
        deployment_service.vm_provisioner.create_snapshot = mock_create_snapshot

        with patch(
            "backend.services.deployment_service.subprocess.run",
            side_effect=FileNotFoundError("docker not found"),
        ):
            config = DeploymentConfig(company_id="comp-123", tenant_name="test", subdomain="test")
            deployment = await deployment_service.create_deployment(config)
            deployment_id = deployment["id"]

            backup = await deployment_service.create_backup(deployment_id)

        assert backup is not None
        assert "deployment_id" in backup
        assert "snapshot_name" in backup
        assert "created_at" in backup
        assert backup["deployment_id"] == deployment_id

    @pytest.mark.asyncio
    async def test_restore_backup(self, deployment_service):
        """Test restoring from backup"""
        config = DeploymentConfig(company_id="comp-123", tenant_name="test", subdomain="test")
        deployment = await deployment_service.create_deployment(config)
        deployment_id = deployment["id"]

        # Set to running
        deployment_service.deployments[deployment_id]["status"] = DeploymentStatus.RUNNING

        # Mock methods
        async def mock_stop_vm(vm_name, force=False):
            pass

        async def mock_restore_snapshot(vm_name, snapshot_name):
            pass

        async def mock_start_vm(vm_name):
            pass

        async def mock_verify(dep_id):
            pass

        deployment_service.vm_provisioner.stop_vm = mock_stop_vm
        deployment_service.vm_provisioner.restore_snapshot = mock_restore_snapshot
        deployment_service.vm_provisioner._start_vm = mock_start_vm
        deployment_service._verify_deployment = mock_verify

        restored = await deployment_service.restore_backup(deployment_id, "backup-123")

        assert restored is not None
        assert restored["id"] == deployment_id

    @pytest.mark.asyncio
    async def test_get_deployment_metrics(self, deployment_service):
        """Test getting deployment metrics"""
        config = DeploymentConfig(company_id="comp-123", tenant_name="test", subdomain="test")
        deployment = await deployment_service.create_deployment(config)
        deployment_id = deployment["id"]

        # Set to running
        deployment_service.deployments[deployment_id]["status"] = DeploymentStatus.RUNNING
        deployment_service.deployments[deployment_id]["health_status"] = "healthy"

        # Mock VM metrics
        async def mock_get_metrics(vm_name):
            return {
                "cpu_usage_percent": 45.5,
                "memory_assigned_mb": 4096,
                "network_in_mbps": 10.5,
                "network_out_mbps": 8.2,
                "disk_read_iops": 100,
                "disk_write_iops": 50,
            }

        deployment_service.vm_provisioner.get_vm_metrics = mock_get_metrics

        metrics = await deployment_service.get_deployment_metrics(deployment_id)

        assert metrics is not None
        assert "deployment_id" in metrics
        assert "status" in metrics
        assert "cpu_usage_percent" in metrics
        assert "memory_usage_mb" in metrics
        assert metrics["cpu_usage_percent"] == 45.5

    @pytest.mark.asyncio
    async def test_get_deployment_metrics_not_running(self, deployment_service):
        """Test getting metrics for non-running deployment"""
        config = DeploymentConfig(company_id="comp-123", tenant_name="test", subdomain="test")
        deployment = await deployment_service.create_deployment(config)
        deployment_id = deployment["id"]

        # Keep as pending
        metrics = await deployment_service.get_deployment_metrics(deployment_id)

        assert metrics is not None
        assert metrics["status"] == "not_running"

    def test_deployment_config_defaults(self):
        """Test DeploymentConfig default values"""
        config = DeploymentConfig(company_id="comp-123", tenant_name="test", subdomain="test")

        assert config.memory_mb == 4096
        assert config.cpu_cores == 2
        assert config.disk_size_gb == 50
        assert config.auto_start is True
        assert config.backup_enabled is True

    def test_deployment_status_enum_values(self):
        """Test DeploymentStatus enum values"""
        assert DeploymentStatus.PENDING.value == "pending"
        assert DeploymentStatus.PROVISIONING.value == "provisioning"
        assert DeploymentStatus.DEPLOYING.value == "deploying"
        assert DeploymentStatus.RUNNING.value == "running"
        assert DeploymentStatus.STOPPED.value == "stopped"
        assert DeploymentStatus.FAILED.value == "failed"
        assert DeploymentStatus.DELETED.value == "deleted"


# Made with Bob
