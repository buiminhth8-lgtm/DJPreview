# 全量质量检查：后端 pytest + 前端 npm ci/build
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

Write-Host "=== check-all: backend ==="
& (Join-Path $PSScriptRoot "check-backend.ps1") -Full
if ($LASTEXITCODE -ne 0) {
    Write-Error "backend check failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "=== check-all: frontend ==="
& (Join-Path $PSScriptRoot "check-frontend.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Error "frontend check failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "=== check-all: ALL OK ==="
