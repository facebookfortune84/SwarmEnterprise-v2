# Copy .env.example to .env when missing (no secrets committed).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Example = Join-Path $Root ".env.example"
$EnvFile = Join-Path $Root ".env"

if (-not (Test-Path $Example)) {
    Write-Error ".env.example not found at $Example"
    exit 1
}

if (Test-Path $EnvFile) {
    Write-Host ".env already exists; leaving unchanged."
    exit 0
}

Copy-Item $Example $EnvFile
Write-Host "Created .env from .env.example. Edit $EnvFile with your values."
