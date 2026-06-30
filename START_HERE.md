# 🚀 START HERE — Launch in 3 Commands

## What to Do RIGHT NOW

### FOR WINDOWS 11 (Run These Commands Now)

**PowerShell (Run as Administrator):**

```powershell
# COMMAND 1: Enable Hyper-V
Enable-WindowsOptionalFeature -FeatureName Hyper-V -Online -All

# When prompted, restart:
Restart-Computer
```

**After restart, continue:**

```powershell
# COMMAND 2: Create Ubuntu VM
# Option A: Use GUI (easier)
# - Open Hyper-V Manager
# - New → Virtual Machine
# - Name: swarmenterprise-vm
# - Gen 2, 8GB RAM, 80GB disk
# - Attach Ubuntu 22.04 ISO, boot

# Option B: PowerShell (faster)
# Download Ubuntu ISO first:
# https://releases.ubuntu.com/jammy/ubuntu-22.04.6-live-server-amd64.iso

# Then run this PowerShell script...
```

**Or use this PowerShell script:**

```powershell
# Save this as create-vm.ps1 and run:
# powershell -ExecutionPolicy Bypass -File create-vm.ps1

$VMName = "swarmenterprise-vm"
$VHDPath = "C:\Hyper-V\swarmenterprise-vm\disk.vhdx"
$ISOPath = "C:\ISO\ubuntu-22.04.6-live-server-amd64.iso"  # Edit this path

# Create VM
New-VM -Name $VMName -Generation 2 -MemoryStartupBytes 8GB -NewVHDPath $VHDPath -NewVHDSizeBytes 80GB
Add-VMDvdDrive -VMName $VMName -ControllerNumber 0 -Path $ISOPath
Set-VMProcessor -VMName $VMName -Count 4
Set-VMMemory -VMName $VMName -DynamicMemoryEnabled $true -MinimumBytes 4GB -MaximumBytes 16GB

# Start it
Start-VM -Name $VMName
Write-Host "VM started! Click Hyper-V Manager to see console and install Ubuntu Server."
```

---

### FOR UBUNTU VM (Install It)

1. **Boot Ubuntu 22.04 LTS from ISO**
2. **Choose:** "Ubuntu Server (automated)"
3. **Install with defaults, enable SSH**
4. **Note the VM's IP address** (shown at end of install)

---

### AFTER UBUNTU BOOTS (From Windows PowerShell)

```powershell
# Replace 192.168.1.100 with your actual VM IP
# Get VM IP from Hyper-V Manager console

# SSH to Ubuntu
ssh ubuntu@192.168.1.100

# Enter password when prompted
```

---

### INSIDE UBUNTU TERMINAL (The Actual Launch!)

**Copy and paste this ENTIRE block into Ubuntu terminal:**

```bash
cd /home/ubuntu && \
wget https://raw.githubusercontent.com/rwv-techsolutions/swarmenterprise-v2/main/launch_ubuntu.sh && \
chmod +x launch_ubuntu.sh && \
bash launch_ubuntu.sh
```

**This takes 10-15 minutes. Wait until you see:**

```
========================================================================
SwarmEnterprise v2 — LAUNCH COMPLETE!
========================================================================
```

---

## ✅ Verify It Worked (From Windows PowerShell)

```powershell
# Test the API
$response = Invoke-RestMethod -Uri "http://192.168.1.100:8000/health" -Method Get
$response | ConvertTo-Json

# Should show:
# "status": "ONLINE"
```

**Open in browser:**
```
http://192.168.1.100:8000/docs
```

---

## 🎉 You're Done!

Your SwarmEnterprise v2 is live at: **http://192.168.1.100:8000**

### Admin Login:
- **Email:** admin@localhost  
- **Password:** AdminPassword123!

---

## 📚 For More Details

- **Full guide:** `WINDOWS_UBUNTU_LAUNCH_GUIDE.md`
- **Quick reference:** `QUICK_REFERENCE.md`
- **Troubleshooting:** See section in WINDOWS_UBUNTU_LAUNCH_GUIDE.md

---

## ⚡ TL;DR Timeline

| Action | Time |
|--------|------|
| Enable Hyper-V + restart | 5 min |
| Create/install Ubuntu | 15 min |
| Ubuntu boot to login | 5 min |
| SSH and run launch script | 15 min |
| **Total** | **40 min** 🚀 |

---

**Ready? Start with the PowerShell commands above!**
