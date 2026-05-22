"""
VM Provisioner - Hyper-V Integration for Self-Hosted Setup

Provisions and manages VMs on Windows Server 2025 Hyper-V for tenant isolation.
Completely free - no cloud costs!
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class VMState(str, Enum):
    """VM states"""
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    FAILED = "failed"
    DELETED = "deleted"


@dataclass
class VMConfig:
    """VM configuration"""
    name: str
    memory_mb: int = 4096
    cpu_cores: int = 2
    disk_size_gb: int = 50
    network_switch: str = "External"
    os_template: str = "ubuntu-22.04"
    domain: str = "realms2riches.tech"


@dataclass
class VMInfo:
    """VM information"""
    name: str
    state: VMState
    ip_address: Optional[str]
    memory_mb: int
    cpu_cores: int
    disk_size_gb: int
    created_at: str
    uptime_seconds: int


class HyperVProvisioner:
    """
    Hyper-V VM provisioner for Windows Server 2025.
    
    Manages VMs for tenant isolation using PowerShell commands.
    Completely free - runs on your own hardware!
    """
    
    def __init__(
        self,
        hyperv_host: str = "localhost",
        scripts_path: Optional[str] = None,
        templates_path: Optional[str] = None,
    ):
        """
        Initialize Hyper-V provisioner.
        
        Args:
            hyperv_host: Hyper-V host (localhost for local, or remote host)
            scripts_path: Path to PowerShell scripts
            templates_path: Path to VM templates
        """
        self.hyperv_host = hyperv_host
        self.scripts_path = scripts_path or os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "hyperv"
        )
        self.templates_path = templates_path or os.path.join(
            os.path.dirname(__file__), "..", "..", "templates", "vms"
        )
        
        logger.info(f"Initialized Hyper-V provisioner: {hyperv_host}")
    
    async def provision_vm(self, config: VMConfig) -> Dict[str, Any]:
        """
        Provision a new VM.
        
        Args:
            config: VM configuration
            
        Returns:
            VM information dict
        """
        try:
            logger.info(f"Provisioning VM: {config.name}")
            
            # Step 1: Create VM
            await self._create_vm(config)
            
            # Step 2: Configure networking
            await self._configure_network(config)
            
            # Step 3: Install OS
            await self._install_os(config)
            
            # Step 4: Configure OS
            await self._configure_os(config)
            
            # Step 5: Install Docker
            await self._install_docker(config)
            
            # Step 6: Start VM
            await self._start_vm(config.name)
            
            # Step 7: Get VM info
            vm_info = await self.get_vm_info(config.name)
            
            logger.info(f"VM provisioned successfully: {config.name}")
            
            return {
                "name": config.name,
                "state": vm_info.state,
                "ip_address": vm_info.ip_address,
                "domain": f"{config.name}.{config.domain}",
                "memory_mb": config.memory_mb,
                "cpu_cores": config.cpu_cores,
                "disk_size_gb": config.disk_size_gb,
            }
            
        except Exception as e:
            logger.error(f"Failed to provision VM {config.name}: {e}")
            # Cleanup on failure
            await self._cleanup_failed_vm(config.name)
            raise
    
    async def _create_vm(self, config: VMConfig) -> None:
        """Create VM using PowerShell"""
        script = f"""
        $VMName = "{config.name}"
        $MemoryMB = {config.memory_mb}
        $CPUCores = {config.cpu_cores}
        $DiskSizeGB = {config.disk_size_gb}
        $SwitchName = "{config.network_switch}"
        
        # Create VM
        New-VM -Name $VMName `
            -MemoryStartupBytes ($MemoryMB * 1MB) `
            -Generation 2 `
            -SwitchName $SwitchName
        
        # Configure CPU
        Set-VMProcessor -VMName $VMName -Count $CPUCores
        
        # Create virtual disk
        $VHDPath = "C:\\Hyper-V\\Virtual Hard Disks\\$VMName.vhdx"
        New-VHD -Path $VHDPath -SizeBytes ($DiskSizeGB * 1GB) -Dynamic
        Add-VMHardDiskDrive -VMName $VMName -Path $VHDPath
        
        # Enable nested virtualization (for Docker)
        Set-VMProcessor -VMName $VMName -ExposeVirtualizationExtensions $true
        
        # Configure dynamic memory
        Set-VMMemory -VMName $VMName -DynamicMemoryEnabled $true `
            -MinimumBytes ($MemoryMB * 0.5 * 1MB) `
            -MaximumBytes ($MemoryMB * 1.5 * 1MB)
        
        Write-Output "VM created: $VMName"
        """
        
        await self._run_powershell(script)
    
    async def _configure_network(self, config: VMConfig) -> None:
        """Configure VM networking"""
        script = f"""
        $VMName = "{config.name}"
        
        # Get network adapter
        $Adapter = Get-VMNetworkAdapter -VMName $VMName
        
        # Enable MAC address spoofing (required for Docker)
        Set-VMNetworkAdapter -VMName $VMName -MacAddressSpoofing On
        
        # Configure VLAN (optional)
        # Set-VMNetworkAdapterVlan -VMName $VMName -Access -VlanId 100
        
        Write-Output "Network configured for: $VMName"
        """
        
        await self._run_powershell(script)
    
    async def _install_os(self, config: VMConfig) -> None:
        """Install OS on VM"""
        # For automated installation, use cloud-init or unattended install
        script = f"""
        $VMName = "{config.name}"
        $ISOPath = "C:\\ISOs\\{config.os_template}.iso"
        
        # Attach ISO
        Add-VMDvdDrive -VMName $VMName -Path $ISOPath
        
        # Set boot order
        $DVD = Get-VMDvdDrive -VMName $VMName
        Set-VMFirmware -VMName $VMName -FirstBootDevice $DVD
        
        # Start VM for installation
        Start-VM -Name $VMName
        
        # Wait for installation (this is simplified - real implementation would monitor)
        Write-Output "OS installation started for: $VMName"
        """
        
        await self._run_powershell(script)
        
        # Wait for OS installation to complete
        # In production, this would monitor the installation progress
        await asyncio.sleep(300)  # 5 minutes - adjust based on your setup
    
    async def _configure_os(self, config: VMConfig) -> None:
        """Configure OS after installation"""
        # This would typically use SSH or PowerShell Direct
        script = f"""
        $VMName = "{config.name}"
        
        # Use PowerShell Direct to configure the VM
        Invoke-Command -VMName $VMName -ScriptBlock {{
            # Set hostname
            hostnamectl set-hostname {config.name}
            
            # Update system
            apt-get update
            apt-get upgrade -y
            
            # Install essential packages
            apt-get install -y curl wget git vim htop net-tools
            
            # Configure firewall
            ufw allow 22/tcp
            ufw allow 80/tcp
            ufw allow 443/tcp
            ufw allow 8080/tcp
            ufw --force enable
            
            # Set timezone
            timedatectl set-timezone UTC
        }}
        
        Write-Output "OS configured for: $VMName"
        """
        
        await self._run_powershell(script)
    
    async def _install_docker(self, config: VMConfig) -> None:
        """Install Docker on VM"""
        script = f"""
        $VMName = "{config.name}"
        
        Invoke-Command -VMName $VMName -ScriptBlock {{
            # Install Docker
            curl -fsSL https://get.docker.com -o get-docker.sh
            sh get-docker.sh
            
            # Add user to docker group
            usermod -aG docker ubuntu
            
            # Install Docker Compose
            curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            chmod +x /usr/local/bin/docker-compose
            
            # Enable Docker service
            systemctl enable docker
            systemctl start docker
            
            # Verify installation
            docker --version
            docker-compose --version
        }}
        
        Write-Output "Docker installed on: $VMName"
        """
        
        await self._run_powershell(script)
    
    async def _start_vm(self, vm_name: str) -> None:
        """Start VM"""
        script = f"""
        $VMName = "{vm_name}"
        
        if ((Get-VM -Name $VMName).State -ne 'Running') {{
            Start-VM -Name $VMName
            Write-Output "VM started: $VMName"
        }} else {{
            Write-Output "VM already running: $VMName"
        }}
        """
        
        await self._run_powershell(script)
    
    async def stop_vm(self, vm_name: str, force: bool = False) -> None:
        """
        Stop VM.
        
        Args:
            vm_name: VM name
            force: Force shutdown if True, graceful if False
        """
        action = "Stop-VM -Force" if force else "Stop-VM"
        
        script = f"""
        $VMName = "{vm_name}"
        
        if ((Get-VM -Name $VMName).State -eq 'Running') {{
            {action} -Name $VMName
            Write-Output "VM stopped: $VMName"
        }} else {{
            Write-Output "VM not running: $VMName"
        }}
        """
        
        await self._run_powershell(script)
    
    async def restart_vm(self, vm_name: str) -> None:
        """Restart VM"""
        script = f"""
        $VMName = "{vm_name}"
        Restart-VM -Name $VMName -Force
        Write-Output "VM restarted: $VMName"
        """
        
        await self._run_powershell(script)
    
    async def delete_vm(self, vm_name: str, delete_disks: bool = True) -> None:
        """
        Delete VM.
        
        Args:
            vm_name: VM name
            delete_disks: Delete virtual disks if True
        """
        script = f"""
        $VMName = "{vm_name}"
        
        # Stop VM if running
        if ((Get-VM -Name $VMName).State -eq 'Running') {{
            Stop-VM -Name $VMName -Force
        }}
        
        # Get disk paths before deletion
        $Disks = Get-VMHardDiskDrive -VMName $VMName | Select-Object -ExpandProperty Path
        
        # Remove VM
        Remove-VM -Name $VMName -Force
        
        # Delete disks if requested
        if ({str(delete_disks).lower()}) {{
            foreach ($Disk in $Disks) {{
                if (Test-Path $Disk) {{
                    Remove-Item $Disk -Force
                    Write-Output "Deleted disk: $Disk"
                }}
            }}
        }}
        
        Write-Output "VM deleted: $VMName"
        """
        
        await self._run_powershell(script)
    
    async def get_vm_info(self, vm_name: str) -> VMInfo:
        """
        Get VM information.
        
        Args:
            vm_name: VM name
            
        Returns:
            VM information
        """
        script = f"""
        $VMName = "{vm_name}"
        $VM = Get-VM -Name $VMName
        
        # Get IP address
        $IP = (Get-VMNetworkAdapter -VMName $VMName).IPAddresses | Where-Object {{$_ -match '^\\d+\\.\\d+\\.\\d+\\.\\d+$'}} | Select-Object -First 1
        
        # Get uptime
        $Uptime = (Get-Date) - $VM.Uptime
        
        # Output as JSON
        @{{
            name = $VM.Name
            state = $VM.State.ToString().ToLower()
            ip_address = $IP
            memory_mb = [int]($VM.MemoryAssigned / 1MB)
            cpu_cores = $VM.ProcessorCount
            created_at = $VM.CreationTime.ToString("o")
            uptime_seconds = [int]$Uptime.TotalSeconds
        }} | ConvertTo-Json
        """
        
        result = await self._run_powershell(script)
        data = json.loads(result)
        
        return VMInfo(
            name=data["name"],
            state=VMState(data["state"]),
            ip_address=data.get("ip_address"),
            memory_mb=data["memory_mb"],
            cpu_cores=data["cpu_cores"],
            disk_size_gb=0,  # Would need additional query
            created_at=data["created_at"],
            uptime_seconds=data["uptime_seconds"],
        )
    
    async def list_vms(self) -> List[VMInfo]:
        """
        List all VMs.
        
        Returns:
            List of VM information
        """
        script = """
        Get-VM | ForEach-Object {
            $IP = (Get-VMNetworkAdapter -VMName $_.Name).IPAddresses | Where-Object {$_ -match '^\\d+\\.\\d+\\.\\d+\\.\\d+$'} | Select-Object -First 1
            $Uptime = (Get-Date) - $_.Uptime
            
            @{
                name = $_.Name
                state = $_.State.ToString().ToLower()
                ip_address = $IP
                memory_mb = [int]($_.MemoryAssigned / 1MB)
                cpu_cores = $_.ProcessorCount
                created_at = $_.CreationTime.ToString("o")
                uptime_seconds = [int]$Uptime.TotalSeconds
            }
        } | ConvertTo-Json
        """
        
        result = await self._run_powershell(script)
        data = json.loads(result)
        
        # Handle single VM (not array)
        if isinstance(data, dict):
            data = [data]
        
        return [
            VMInfo(
                name=vm["name"],
                state=VMState(vm["state"]),
                ip_address=vm.get("ip_address"),
                memory_mb=vm["memory_mb"],
                cpu_cores=vm["cpu_cores"],
                disk_size_gb=0,
                created_at=vm["created_at"],
                uptime_seconds=vm["uptime_seconds"],
            )
            for vm in data
        ]
    
    async def get_vm_metrics(self, vm_name: str) -> Dict[str, Any]:
        """
        Get VM performance metrics.
        
        Args:
            vm_name: VM name
            
        Returns:
            Metrics dict
        """
        script = f"""
        $VMName = "{vm_name}"
        $VM = Get-VM -Name $VMName
        $Metrics = Measure-VM -Name $VMName
        
        @{{
            cpu_usage_percent = [int]$Metrics.AvgCPUUsage
            memory_assigned_mb = [int]($VM.MemoryAssigned / 1MB)
            memory_demand_mb = [int]($VM.MemoryDemand / 1MB)
            network_in_mbps = [int]($Metrics.NetworkMeteredTrafficReport[0].IncomingTrafficTotal / 1MB)
            network_out_mbps = [int]($Metrics.NetworkMeteredTrafficReport[0].OutgoingTrafficTotal / 1MB)
            disk_read_iops = [int]$Metrics.AggregatedAverageNormalizedIOPS
            disk_write_iops = [int]$Metrics.AggregatedAverageNormalizedIOPS
        }} | ConvertTo-Json
        """
        
        result = await self._run_powershell(script)
        return json.loads(result)
    
    async def create_snapshot(self, vm_name: str, snapshot_name: str) -> None:
        """Create VM snapshot"""
        script = f"""
        $VMName = "{vm_name}"
        $SnapshotName = "{snapshot_name}"
        
        Checkpoint-VM -Name $VMName -SnapshotName $SnapshotName
        Write-Output "Snapshot created: $SnapshotName for $VMName"
        """
        
        await self._run_powershell(script)
    
    async def restore_snapshot(self, vm_name: str, snapshot_name: str) -> None:
        """Restore VM from snapshot"""
        script = f"""
        $VMName = "{vm_name}"
        $SnapshotName = "{snapshot_name}"
        
        Restore-VMSnapshot -VMName $VMName -Name $SnapshotName -Confirm:$false
        Write-Output "Snapshot restored: $SnapshotName for $VMName"
        """
        
        await self._run_powershell(script)
    
    async def _cleanup_failed_vm(self, vm_name: str) -> None:
        """Cleanup failed VM"""
        try:
            await self.delete_vm(vm_name, delete_disks=True)
            logger.info(f"Cleaned up failed VM: {vm_name}")
        except Exception as e:
            logger.error(f"Failed to cleanup VM {vm_name}: {e}")
    
    async def _run_powershell(self, script: str) -> str:
        """
        Run PowerShell script.
        
        Args:
            script: PowerShell script
            
        Returns:
            Script output
        """
        try:
            # Run PowerShell command
            process = await asyncio.create_subprocess_exec(
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                raise Exception(f"PowerShell error: {error_msg}")
            
            return stdout.decode().strip()
            
        except Exception as e:
            logger.error(f"PowerShell execution failed: {e}")
            raise


# Example usage
if __name__ == "__main__":
    async def main():
        provisioner = HyperVProvisioner()
        
        # Create VM config
        config = VMConfig(
            name="tenant-demo",
            memory_mb=4096,
            cpu_cores=2,
            disk_size_gb=50,
            network_switch="External",
            os_template="ubuntu-22.04",
            domain="realms2riches.tech",
        )
        
        # Provision VM
        vm_info = await provisioner.provision_vm(config)
        print(f"VM provisioned: {vm_info}")
        
        # Get VM info
        info = await provisioner.get_vm_info(config.name)
        print(f"VM info: {info}")
        
        # Get metrics
        metrics = await provisioner.get_vm_metrics(config.name)
        print(f"VM metrics: {metrics}")
        
        # List all VMs
        vms = await provisioner.list_vms()
        print(f"All VMs: {vms}")
    
    asyncio.run(main())

# Made with Bob
