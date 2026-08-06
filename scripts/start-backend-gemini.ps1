# 启动后端（Gemini OpenAI-compatible 线上 Provider profile）。
# 用法：
#   .\scripts\start-backend-gemini.ps1
#   .\scripts\start-backend-gemini.ps1 -Port 8010
#   .\scripts\start-backend-gemini.ps1 -NoReload
# 不会打印任何 API key（含 GEMINI_API_KEY）。
#
# 启动前请确认：
#   1. 已复制 example：Copy-Item .gemini.env.example .gemini.env
#   2. 已在 .gemini.env 填入真实 GEMINI_API_KEY（仅保留本地，不要提交）

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
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GEMINI_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:GEMINI_MODEL -ErrorAction SilentlyContinue
Remove-Item Env:DEEPSEEK_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:DEEPSEEK_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:DEEPSEEK_MODEL -ErrorAction SilentlyContinue
Remove-Item Env:LMSTUDIO_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:LMSTUDIO_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:LMSTUDIO_MODEL -ErrorAction SilentlyContinue

$env:LLM_ENV_PROFILE = "gemini"

$ExpectedEnv = Join-Path $ProjectRoot ".gemini.env"
if (-not (Test-Path $ExpectedEnv)) {
  Write-Warning "Expected env file not found: .gemini.env"
  Write-Warning "Copy example first: Copy-Item .gemini.env.example .gemini.env"
}

Write-Host "Starting backend with Gemini profile"
Write-Host "Expected env file: .gemini.env"
Write-Host "This profile may call external Gemini API if configured"
Write-Host "Host: $HostAddress  Port: $Port"

$Args = @("services.api.main:app", "--host", $HostAddress, "--port", "$Port")
if (-not $NoReload) {
  $Args += "--reload"
}

python -m uvicorn @Args
