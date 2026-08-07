<#
.SYNOPSIS
    下载 GeneralUser GS SoundFont（.sf2）、LICENSE 与 README 到 data/soundfonts/。
.DESCRIPTION
    从 GeneralUser GS 官方 GitHub 仓库（mrbumpy409/GeneralUser-GS）下载音源与文档，
    自动放入项目 data/soundfonts/ 目录。主要服务 Windows PowerShell 开发环境。
    - 未传 -AcceptLicense 时会交互确认许可，输入 YES 才继续。
    - 下载后校验：文件存在、.sf2 大小 > 1MB、RIFF 文件头。
    - 自动补充 .gitignore，避免真实 .sf2/.sf3/.sfz 被提交。
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\download_generaluser_gs.ps1 -AcceptLicense
.PARAMETER ProjectRoot
    项目根目录；留空则从当前目录向上自动查找。
.PARAMETER TargetDir
    下载目标目录；留空则使用 <ProjectRoot>\data\soundfonts。
.PARAMETER Force
    已存在的文件也重新下载覆盖。
.PARAMETER AcceptLicense
    跳过交互确认，视为已接受许可。
#>

param(
    [string]$ProjectRoot = "",
    [string]$TargetDir = "",
    [switch]$Force,
    [switch]$AcceptLicense
)

$ErrorActionPreference = "Stop"

# ---------- 输出辅助 ----------

function Write-Step([string]$message) {
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Write-Ok([string]$message) {
    Write-Host "[OK] $message" -ForegroundColor Green
}

function Write-Warn([string]$message) {
    Write-Host "[WARN] $message" -ForegroundColor Yellow
}

function Write-Fail([string]$message) {
    Write-Host "[ERROR] $message" -ForegroundColor Red
}

# ---------- 定位项目根目录 ----------

function Resolve-ProjectRoot {
    param([string]$Root)

    if ($Root -and (Test-Path -LiteralPath $Root)) {
        return (Resolve-Path -LiteralPath $Root).Path
    }
    if ($Root -and -not (Test-Path -LiteralPath $Root)) {
        Write-Warn "指定的 ProjectRoot 不存在：$Root，改为自动查找。"
    }

    $current = (Get-Location).Path
    $candidates = @(
        "apps\web\package.json",
        "apps\web",
        "services",
        "packages"
    )
    while ($current) {
        foreach ($candidate in $candidates) {
            if (Test-Path -LiteralPath (Join-Path $current $candidate)) {
                return $current
            }
        }
        $parent = Split-Path -Path $current -Parent
        if ($parent -eq $current) {
            break
        }
        $current = $parent
    }
    throw "无法自动定位项目根目录，请使用 -ProjectRoot 显式指定。"
}

# ---------- 下载文件 ----------

function Download-File {
    param(
        [string]$Url,
        [string]$OutFile,
        [switch]$ForceFile
    )

    if (Test-Path -LiteralPath $OutFile) {
        if (-not $ForceFile) {
            Write-Ok "已存在，跳过：$OutFile"
            return $true
        }
        Write-Warn "Force：覆盖已存在文件 $OutFile"
    }

    $tmpFile = "$OutFile.tmp"
    try {
        Invoke-WebRequest -Uri $Url -OutFile $tmpFile -UseBasicParsing
    } catch {
        Write-Fail "下载失败：$Url"
        if (Test-Path -LiteralPath $tmpFile) {
            Remove-Item -LiteralPath $tmpFile -Force -ErrorAction SilentlyContinue
        }
        throw
    }

    if (-not (Test-Path -LiteralPath $tmpFile)) {
        throw "下载后未生成临时文件：$tmpFile"
    }
    Move-Item -LiteralPath $tmpFile -Destination $OutFile -Force
    Write-Ok "已下载：$OutFile"
    return $true
}

# ---------- 主流程 ----------

$projectRoot = Resolve-ProjectRoot -Root $ProjectRoot
Write-Step "项目根目录：$projectRoot"

if ($TargetDir) {
    $targetDir = $TargetDir
} else {
    $targetDir = Join-Path $projectRoot "data\soundfonts"
}
New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
Write-Ok "SoundFont 目录：$targetDir"

# 许可提示
if (-not $AcceptLicense) {
    Write-Step "许可提示"
    Write-Host ""
    Write-Host "GeneralUser GS 是 Roland GS / General MIDI 兼容 SoundFont。"
    Write-Host "该脚本仅为本地开发和试听下载音源。"
    Write-Host "SoundFont 文件较大，不应提交到 Git。"
    Write-Host "如果你要把音源随软件分发或用于商业发行，请阅读随包 LICENSE。"
    Write-Host "继续下载表示你确认自己会遵守 GeneralUser GS 的许可说明。"
    Write-Host ""
    $answer = Read-Host "输入 YES 以继续，或任意其他内容取消"
    if ($answer -ne "YES") {
        Write-Warn "已取消。"
        exit 1
    }
    Write-Ok "已确认接受许可。"
} else {
    Write-Ok "已通过 -AcceptLicense 确认许可。"
}

$base = "https://raw.githubusercontent.com/mrbumpy409/GeneralUser-GS/main"

$sf2Url = "$base/GeneralUser-GS.sf2"
$licenseUrl = "$base/documentation/LICENSE.txt"
$readmeUrl = "$base/documentation/README.md"

$sf2File = Join-Path $targetDir "GeneralUser-GS.sf2"
$licenseFile = Join-Path $targetDir "GeneralUser-GS-LICENSE.txt"
$readmeFile = Join-Path $targetDir "GeneralUser-GS-README.md"

Write-Step "下载 GeneralUser-GS.sf2"
Download-File -Url $sf2Url -OutFile $sf2File -ForceFile:$Force

Write-Step "下载 GeneralUser-GS-LICENSE.txt"
Download-File -Url $licenseUrl -OutFile $licenseFile -ForceFile:$Force

Write-Step "下载 GeneralUser-GS-README.md"
Download-File -Url $readmeUrl -OutFile $readmeFile -ForceFile:$Force

# 校验
Write-Step "校验下载文件"
foreach ($file in @($sf2File, $licenseFile, $readmeFile)) {
    if (-not (Test-Path -LiteralPath $file)) {
        throw "文件不存在：$file"
    }
    $size = (Get-Item -LiteralPath $file).Length
    if ($size -le 0) {
        throw "文件为空：$file"
    }
}

$sf2Size = (Get-Item -LiteralPath $sf2File).Length
if ($sf2Size -le 1MB) {
    Write-Warn ".sf2 大小 $([math]::Round($sf2Size/1MB, 2)) MB 未超过 1MB，可能下载不完整。"
}

$bytes = [System.IO.File]::ReadAllBytes($sf2File)[0..3]
$header = [System.Text.Encoding]::ASCII.GetString($bytes)
if ($header -ne "RIFF") {
    throw "GeneralUser-GS.sf2 文件头不是 RIFF，可能不是合法的 SoundFont 文件。"
}
Write-Ok "校验通过：GeneralUser-GS.sf2（$([math]::Round($sf2Size/1MB, 2)) MB），文件头 RIFF。"
Write-Ok "校验通过：GeneralUser-GS-LICENSE.txt / GeneralUser-GS-README.md"

# 补充 .gitignore
Write-Step "补充 .gitignore"
$gitignorePath = Join-Path $projectRoot ".gitignore"
$ignoreEntries = @(
    "data/soundfonts/*.sf2",
    "data/soundfonts/*.sf3",
    "data/soundfonts/*.sfz"
)
$changed = $false
if (Test-Path -LiteralPath $gitignorePath) {
    $content = Get-Content -LiteralPath $gitignorePath -Raw
    foreach ($entry in $ignoreEntries) {
        if ($content -notmatch [regex]::Escape($entry)) {
            Add-Content -LiteralPath $gitignorePath -Value $entry -Encoding UTF8
            Write-Ok "已追加 .gitignore：$entry"
            $changed = $true
        }
    }
} else {
    $ignoreEntries | Set-Content -LiteralPath $gitignorePath -Encoding UTF8
    Write-Ok "已创建 .gitignore"
    $changed = $true
}
if (-not $changed) {
    Write-Ok ".gitignore 已包含 soundfont 忽略规则，无需修改。"
}

# 输出环境变量与启动命令
Write-Step "后续启动命令"
Write-Host ""
Write-Host "启动后端前设置环境变量："
Write-Host ""
Write-Host "`$env:AUDIO_RENDERER=`"auto`""
Write-Host "`$env:SOUNDFONT_DIR=`"$targetDir`""
Write-Host "`$env:SOUNDFONT_PATH=`"$sf2File`""
Write-Host ""
Write-Host "启动后端："
Write-Host ""
Write-Host "uvicorn services.api.main:app --reload --host 127.0.0.1 --port 8000"
Write-Host ""
Write-Host "然后在前端 SoundFont 面板点击扫描，选择 GeneralUser-GS.sf2，并重新渲染 WAV。"
Write-Host ""
Write-Ok "完成。"
