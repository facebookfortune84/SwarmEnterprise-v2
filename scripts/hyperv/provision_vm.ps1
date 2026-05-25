# Hyper-V VM stub for tenant isolation (full automation optional)
param(
    [Parameter(Mandatory = $true)][string]$TenantId,
    [Parameter(Mandatory = $true)][string]$VmName
)

Write-Host "[STUB] Would provision Hyper-V VM: $VmName for tenant $TenantId"
Write-Host "See DEPLOY.md — nested WSL2 Ubuntu + Docker per tenant VM"
# Example (requires Hyper-V admin, not executed):
# New-VM -Name $VmName -MemoryStartupBytes 4GB -Generation 2
# Install Ubuntu WSL2 inside VM, then docker compose for tenant box

exit 0
