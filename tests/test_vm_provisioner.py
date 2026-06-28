"""
Tests for backend/orchestration/vm_provisioner.py
All subprocess/asyncio.create_subprocess_exec calls are mocked.
"""
import json
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from backend.orchestration.vm_provisioner import (
    HyperVProvisioner,
    VMConfig,
    VMInfo,
    VMState,
)


def _make_provisioner():
    return HyperVProvisioner(hyperv_host="localhost")


# Helper: patch _run_powershell with a success return
def _ps_success(output: str = "OK"):
    return patch.object(HyperVProvisioner, "_run_powershell", new_callable=AsyncMock, return_value=output)


class TestRunPowershell:
    @pytest.mark.asyncio
    async def test_run_powershell_success(self):
        provisioner = _make_provisioner()
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"hello world", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await provisioner._run_powershell("Get-VM")
        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_run_powershell_failure(self):
        provisioner = _make_provisioner()
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"error message"))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with pytest.raises(Exception, match="PowerShell error"):
                await provisioner._run_powershell("Bad-Command")

    @pytest.mark.asyncio
    async def test_run_powershell_exception_propagated(self):
        provisioner = _make_provisioner()
        with patch("asyncio.create_subprocess_exec", side_effect=OSError("no powershell")):
            with pytest.raises(Exception):
                await provisioner._run_powershell("something")


class TestProvisionVM:
    @pytest.mark.asyncio
    async def test_provision_vm_success(self):
        provisioner = _make_provisioner()
        config = VMConfig(name="test-vm", memory_mb=2048, cpu_cores=2, disk_size_gb=20)

        vm_info = VMInfo(
            name="test-vm",
            state=VMState.RUNNING,
            ip_address="10.0.0.1",
            memory_mb=2048,
            cpu_cores=2,
            disk_size_gb=20,
            created_at=datetime.utcnow().isoformat(),
            uptime_seconds=0,
        )

        with patch.object(provisioner, "_create_vm", new_callable=AsyncMock), \
             patch.object(provisioner, "_configure_network", new_callable=AsyncMock), \
             patch.object(provisioner, "_install_os", new_callable=AsyncMock), \
             patch.object(provisioner, "_configure_os", new_callable=AsyncMock), \
             patch.object(provisioner, "_install_docker", new_callable=AsyncMock), \
             patch.object(provisioner, "_start_vm", new_callable=AsyncMock), \
             patch.object(provisioner, "get_vm_info", new_callable=AsyncMock, return_value=vm_info):
            result = await provisioner.provision_vm(config)

        assert result["name"] == "test-vm"
        assert result["ip_address"] == "10.0.0.1"

    @pytest.mark.asyncio
    async def test_provision_vm_failure_triggers_cleanup(self):
        provisioner = _make_provisioner()
        config = VMConfig(name="fail-vm")

        with patch.object(provisioner, "_create_vm", new_callable=AsyncMock, side_effect=RuntimeError("create failed")), \
             patch.object(provisioner, "_cleanup_failed_vm", new_callable=AsyncMock) as mock_cleanup:
            with pytest.raises(RuntimeError, match="create failed"):
                await provisioner.provision_vm(config)
        mock_cleanup.assert_called_once_with("fail-vm")


class TestStopVM:
    @pytest.mark.asyncio
    async def test_stop_vm_graceful(self):
        provisioner = _make_provisioner()
        with _ps_success("VM stopped: test-vm"):
            await provisioner.stop_vm("test-vm", force=False)

    @pytest.mark.asyncio
    async def test_stop_vm_force(self):
        provisioner = _make_provisioner()
        with _ps_success("VM stopped: test-vm"):
            await provisioner.stop_vm("test-vm", force=True)

    @pytest.mark.asyncio
    async def test_stop_vm_powershell_error(self):
        provisioner = _make_provisioner()
        with patch.object(
            provisioner, "_run_powershell", new_callable=AsyncMock,
            side_effect=Exception("PowerShell error: access denied")
        ):
            with pytest.raises(Exception):
                await provisioner.stop_vm("bad-vm")


class TestRestartVM:
    @pytest.mark.asyncio
    async def test_restart_vm(self):
        provisioner = _make_provisioner()
        with _ps_success("VM restarted: test-vm"):
            await provisioner.restart_vm("test-vm")


class TestDeleteVM:
    @pytest.mark.asyncio
    async def test_delete_vm_with_disks(self):
        provisioner = _make_provisioner()
        with _ps_success("VM deleted: test-vm"):
            await provisioner.delete_vm("test-vm", delete_disks=True)

    @pytest.mark.asyncio
    async def test_delete_vm_without_disks(self):
        provisioner = _make_provisioner()
        with _ps_success("VM deleted: test-vm"):
            await provisioner.delete_vm("test-vm", delete_disks=False)


class TestGetVMInfo:
    @pytest.mark.asyncio
    async def test_get_vm_info_success(self):
        provisioner = _make_provisioner()
        vm_data = {
            "name": "test-vm",
            "state": "running",
            "ip_address": "10.0.0.5",
            "memory_mb": 4096,
            "cpu_cores": 2,
            "created_at": "2024-01-01T00:00:00",
            "uptime_seconds": 3600,
        }
        with patch.object(
            provisioner, "_run_powershell", new_callable=AsyncMock,
            return_value=json.dumps(vm_data)
        ):
            info = await provisioner.get_vm_info("test-vm")
        assert info.name == "test-vm"
        assert info.state == VMState.RUNNING
        assert info.ip_address == "10.0.0.5"

    @pytest.mark.asyncio
    async def test_get_vm_info_powershell_error(self):
        provisioner = _make_provisioner()
        with patch.object(
            provisioner, "_run_powershell", new_callable=AsyncMock,
            side_effect=Exception("PowerShell error: VM not found")
        ):
            with pytest.raises(Exception):
                await provisioner.get_vm_info("missing-vm")


class TestListVMs:
    @pytest.mark.asyncio
    async def test_list_vms_multiple(self):
        provisioner = _make_provisioner()
        vm_list = [
            {
                "name": "vm-1",
                "state": "running",
                "ip_address": "10.0.0.1",
                "memory_mb": 2048,
                "cpu_cores": 2,
                "created_at": "2024-01-01T00:00:00",
                "uptime_seconds": 100,
            },
            {
                "name": "vm-2",
                "state": "stopped",
                "ip_address": None,
                "memory_mb": 4096,
                "cpu_cores": 4,
                "created_at": "2024-01-02T00:00:00",
                "uptime_seconds": 0,
            },
        ]
        with patch.object(
            provisioner, "_run_powershell", new_callable=AsyncMock,
            return_value=json.dumps(vm_list)
        ):
            vms = await provisioner.list_vms()
        assert len(vms) == 2
        assert vms[0].name == "vm-1"
        assert vms[1].state == VMState.STOPPED

    @pytest.mark.asyncio
    async def test_list_vms_single_not_array(self):
        """list_vms must handle PowerShell returning a single dict (not array)."""
        provisioner = _make_provisioner()
        single_vm = {
            "name": "vm-1",
            "state": "running",
            "ip_address": "10.0.0.1",
            "memory_mb": 2048,
            "cpu_cores": 2,
            "created_at": "2024-01-01T00:00:00",
            "uptime_seconds": 200,
        }
        with patch.object(
            provisioner, "_run_powershell", new_callable=AsyncMock,
            return_value=json.dumps(single_vm)
        ):
            vms = await provisioner.list_vms()
        assert len(vms) == 1


class TestGetVMMetrics:
    @pytest.mark.asyncio
    async def test_get_vm_metrics_success(self):
        provisioner = _make_provisioner()
        metrics_data = {
            "cpu_usage_percent": 15,
            "memory_assigned_mb": 2048,
            "memory_demand_mb": 1024,
            "network_in_mbps": 10,
            "network_out_mbps": 5,
            "disk_read_iops": 100,
            "disk_write_iops": 50,
        }
        with patch.object(
            provisioner, "_run_powershell", new_callable=AsyncMock,
            return_value=json.dumps(metrics_data)
        ):
            result = await provisioner.get_vm_metrics("test-vm")
        assert result["cpu_usage_percent"] == 15


class TestSnapshots:
    @pytest.mark.asyncio
    async def test_create_snapshot(self):
        provisioner = _make_provisioner()
        with _ps_success("Snapshot created"):
            await provisioner.create_snapshot("test-vm", "snap-001")

    @pytest.mark.asyncio
    async def test_restore_snapshot(self):
        provisioner = _make_provisioner()
        with _ps_success("Snapshot restored"):
            await provisioner.restore_snapshot("test-vm", "snap-001")


class TestCleanupFailedVM:
    @pytest.mark.asyncio
    async def test_cleanup_success(self):
        provisioner = _make_provisioner()
        with patch.object(provisioner, "delete_vm", new_callable=AsyncMock):
            await provisioner._cleanup_failed_vm("fail-vm")

    @pytest.mark.asyncio
    async def test_cleanup_failure_is_silent(self):
        """_cleanup_failed_vm should not re-raise on failure."""
        provisioner = _make_provisioner()
        with patch.object(
            provisioner, "delete_vm", new_callable=AsyncMock,
            side_effect=Exception("delete failed")
        ):
            # Should not raise
            await provisioner._cleanup_failed_vm("fail-vm")


class TestVMStateEnum:
    def test_all_states(self):
        assert VMState.CREATING == "creating"
        assert VMState.RUNNING == "running"
        assert VMState.STOPPED == "stopped"
        assert VMState.PAUSED == "paused"
        assert VMState.FAILED == "failed"
        assert VMState.DELETED == "deleted"
