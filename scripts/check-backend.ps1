# 后端质量检查：默认运行快速回归（跳过 slow 集成测试）；-Full 运行全量 pytest
param(
    [switch]$Full
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$env:LLM_PROVIDER = "mock"
$env:AUDIO_RENDERER = "fallback"
$env:PYTHONPATH = (Get-Location).Path

if ($Full) {
    Write-Host "[check-backend] Running full pytest ..."
} else {
    Write-Host "[check-backend] Running fast pytest (skip slow integration tests) ..."
}
# 使用项目内 .pytest-tmp 作为 basetemp，避免 Windows 上用户 Temp 目录 ACL 权限问题
$tmp = Join-Path $root ".pytest-tmp"
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
if ($Full) {
    python -m pytest -q --basetemp $tmp
} else {
    python -m pytest -q -m "not slow" --basetemp $tmp
}
if ($LASTEXITCODE -ne 0) {
    Write-Error "[check-backend] pytest failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
Write-Host "[check-backend] OK"
