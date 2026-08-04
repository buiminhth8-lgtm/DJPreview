# 前端质量检查：npm ci + npm run build
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$web = Join-Path $root "apps\web"
if (-not (Test-Path -LiteralPath $web)) {
    Write-Error "[check-frontend] 未找到前端目录：$web"
    exit 1
}
Set-Location -LiteralPath $web

Write-Host "[check-frontend] npm ci ..."
npm ci --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[check-frontend] npm run build ..."
npm run build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Set-Location -LiteralPath $root
Write-Host "[check-frontend] OK"
