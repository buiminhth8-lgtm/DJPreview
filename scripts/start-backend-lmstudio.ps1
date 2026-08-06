# 启动后端（LM Studio 本地 Provider profile）。
# 用法：
#   .\scripts\start-backend-lmstudio.ps1
#   .\scripts\start-backend-lmstudio.ps1 -Port 8010
#   .\scripts\start-backend-lmstudio.ps1 -NoReload
# 不会打印任何 API key；不强制检查 LM Studio 是否可访问，仅提示。
#
# 启动前请确认：
#   1. 已复制 example：Copy-Item .lmstudio.env.example .lmstudio.env
#   2. 已在 .lmstudio.env 配置 LMSTUDIO_MODEL 为 LM Studio 中已加载的模型名
#   3. LM Studio local server 已启动（默认 http://127.0.0.1:1234/v1）

param(
  [string]$HostAddress = "127.0.0.1",
  [int]$Port = 8000,
  [switch]$NoReload
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $ProjectRoot

$VenvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
  . $VenvActivate
} else {
  Write-Warning "Virtualenv not found at .venv\Scripts\Activate.ps1"
}

# 清理 provider 相关环境变量，避免 profile 污染
Remove-Item Env:LLM_PROVIDER -ErrorAction SilentlyContinue
Remove-Item Env:DEEPSEEK_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:DEEPSEEK_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:DEEPSEEK_MODEL -ErrorAction SilentlyContinue
Remove-Item Env:LMSTUDIO_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:LMSTUDIO_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:LMSTUDIO_MODEL -ErrorAction SilentlyContinue

$env:LLM_ENV_PROFILE = "lmstudio"

$ExpectedEnv = Join-Path $ProjectRoot ".lmstudio.env"
if (-not (Test-Path $ExpectedEnv)) {
  Write-Warning "Expected env file not found: .lmstudio.env"
  Write-Warning "Copy example first: Copy-Item .lmstudio.env.example .lmstudio.env"
}

Write-Host "Starting backend with LM Studio profile"
Write-Host "Expected env file: .lmstudio.env"
Write-Host "Make sure LM Studio local server is running"
Write-Host "Default example base URL: http://127.0.0.1:1234/v1"
Write-Host "Host: $HostAddress  Port: $Port"

$Args = @("services.api.main:app", "--host", $HostAddress, "--port", "$Port")
if (-not $NoReload) {
  $Args += "--reload"
}

python -m uvicorn @Args
