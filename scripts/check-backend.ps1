# 后端质量检查：运行 pytest（MockProvider + fallback renderer）
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$env:LLM_PROVIDER = "mock"
$env:AUDIO_RENDERER = "fallback"
$env:PYTHONPATH = (Get-Location).Path

Write-Host "[check-backend] Running pytest ..."
# 使用项目内 .pytest-tmp 作为 basetemp，避免 Windows 上用户 Temp 目录 ACL 权限问题
$tmp = Join-Path $root ".pytest-tmp"
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
python -m pytest -q --basetemp $tmp
if ($LASTEXITCODE -ne 0) {
    Write-Error "[check-backend] pytest failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
Write-Host "[check-backend] OK"
