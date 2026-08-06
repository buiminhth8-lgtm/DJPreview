# 启动后端（MockProvider profile）。
# 用法：
#   .\scripts\start-backend-mock.ps1
#   .\scripts\start-backend-mock.ps1 -Port 8010
#   .\scripts\start-backend-mock.ps1 -NoReload
# 不会打印任何 API key。

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

$env:LLM_ENV_PROFILE = "mock"

$ExpectedEnv = Join-Path $ProjectRoot ".mock.env"
if (-not (Test-Path $ExpectedEnv)) {
  Write-Warning "Expected env file not found: .mock.env"
  Write-Warning "Copy example first: Copy-Item .mock.env.example .mock.env"
}

Write-Host "Starting backend with MockProvider profile"
Write-Host "Expected env file: .mock.env"
Write-Host "Mode: mock (稳定回归测试，不调用外部模型)"
Write-Host "Host: $HostAddress  Port: $Port"

$Args = @("services.api.main:app", "--host", $HostAddress, "--port", "$Port")
if (-not $NoReload) {
  $Args += "--reload"
}

python -m uvicorn @Args
