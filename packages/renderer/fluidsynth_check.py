"""FluidSynth 可用性检测与 SoundFont 文件校验（T39-B / T39-C）。

- detect_fluidsynth()：检测系统 FluidSynth 是否可用（env → PATH → -V → --version）。
- validate_soundfont_file()：校验 SoundFont 文件存在 / 可读 / 格式 / RIFF 头。
这些函数是纯诊断工具，不改变渲染核心逻辑；不可用时由调用方决定 fallback。
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

SUPPORTED_EXTENSIONS = (".sf2", ".sf3", ".sfz")

# 版本检测参数顺序：Windows / Chocolatey 下 --version 可能报 "Unknown switch '-'"，
# 优先使用 -V。绝不使用 -version（会加载默认 SoundFont 并进入交互 console）。
VERSION_ARGS = ("-V", "--version")

# 每个版本检测命令的超时（秒）
VERSION_TIMEOUT_SECONDS = 3.0


def _resolve_binary() -> tuple[str | None, str | None]:
    """解析 fluidsynth 可执行文件路径。

    返回 (binary, error)。优先环境变量 FLUIDSYNTH_BIN / FLUIDSYNTH_PATH；
    值为完整路径时直接使用，值为裸命令名（如 "fluidsynth"）时用 shutil.which 解析；
    都找不到才返回 not found。
    """
    raw = os.getenv("FLUIDSYNTH_BIN", "").strip() or os.getenv("FLUIDSYNTH_PATH", "").strip() or ""
    if raw:
        if Path(raw).exists():
            return str(Path(raw).resolve()), None
        resolved = shutil.which(raw)
        if resolved:
            return resolved, None
        return raw, f"FLUIDSYNTH_BIN 指定 {raw!r} 但 PATH 中找不到该命令"
    found = shutil.which("fluidsynth") or shutil.which("fluidsynth.exe")
    if found:
        return found, None
    return None, "fluidsynth not found in PATH"


def detect_fluidsynth() -> dict:
    """检测 FluidSynth 是否可用，返回结构化状态。

    1. 解析 binary（环境变量 → PATH）。
    2. 按顺序尝试版本检测参数：-V → --version。
    3. 任一成功即可用；都失败才不可用，并收集 version_check_errors。
    4. 每个命令设置 timeout，捕获 not found / 权限 / 超时 / 非零退出。
    不会抛出异常：FluidSynth 不可用时返回 available=False。
    """
    binary, resolve_error = _resolve_binary()
    if binary is None:
        return {
            "available": False,
            "binary": None,
            "version": None,
            "version_arg": None,
            "version_check_errors": [],
            "error": resolve_error or "fluidsynth not found",
        }

    version_check_errors: list[dict] = []
    for arg in VERSION_ARGS:
        try:
            proc = subprocess.run(
                [binary, arg],
                capture_output=True,
                text=True,
                timeout=VERSION_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            version_check_errors.append(
                {"arg": arg, "returncode": None, "stderr": f"timeout: {exc}"}
            )
            continue
        except (OSError, PermissionError) as exc:
            version_check_errors.append(
                {"arg": arg, "returncode": None, "stderr": f"cannot execute: {exc}"}
            )
            continue

        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()[-500:]
            version_check_errors.append(
                {"arg": arg, "returncode": proc.returncode, "stderr": detail}
            )
            continue

        first_line = (proc.stdout or proc.stderr or "").strip().splitlines()
        version = first_line[0].strip() if first_line else None
        return {
            "available": True,
            "binary": binary,
            "version": version,
            "version_arg": arg,
            "version_check_errors": version_check_errors,
            "error": None,
        }

    # 所有版本检测方式都失败
    return {
        "available": False,
        "binary": binary,
        "version": None,
        "version_arg": None,
        "version_check_errors": version_check_errors,
        "error": f"FluidSynth binary found but version check failed: "
        f"{version_check_errors[-1]['stderr'] if version_check_errors else 'unknown'}",
    }


def validate_soundfont_file(path: str | Path | None) -> dict:
    """校验 SoundFont 文件，返回结构化状态。

    - 不存在 → error = "soundfont_file_missing"
    - 不可读 → error = "permission denied"
    - 后缀不支持 → error = "unsupported format"
    - .sf2 文件头不是 RIFF → error = "invalid RIFF header"
    - .sf3 / .sfz 不做 RIFF 校验（避免误判失败）
    """
    if not path:
        return {
            "exists": False,
            "readable": False,
            "format": None,
            "size_bytes": 0,
            "valid": False,
            "error": "soundfont_file_missing",
        }

    p = Path(path)
    if not p.exists() or not p.is_file():
        return {
            "exists": False,
            "readable": False,
            "format": None,
            "size_bytes": 0,
            "valid": False,
            "error": "soundfont_file_missing",
        }

    suffix = p.suffix.lower()
    try:
        size = p.stat().st_size
        with open(p, "rb"):
            pass
    except (PermissionError, OSError) as exc:
        return {
            "exists": True,
            "readable": False,
            "format": suffix or None,
            "size_bytes": 0,
            "valid": False,
            "error": f"permission denied：{exc}",
        }

    if suffix not in SUPPORTED_EXTENSIONS:
        return {
            "exists": True,
            "readable": True,
            "format": suffix or None,
            "size_bytes": size,
            "valid": False,
            "error": "unsupported format（仅支持 .sf2 / .sf3 / .sfz）",
        }

    if suffix == ".sf2":
        try:
            with open(p, "rb") as f:
                header = f.read(4)
        except OSError as exc:
            return {
                "exists": True,
                "readable": False,
                "format": suffix,
                "size_bytes": size,
                "valid": False,
                "error": f"读取失败：{exc}",
            }
        if header != b"RIFF":
            return {
                "exists": True,
                "readable": True,
                "format": suffix,
                "size_bytes": size,
                "valid": False,
                "error": "invalid RIFF header（不是合法的 .sf2 文件）",
            }

    return {
        "exists": True,
        "readable": True,
        "format": suffix,
        "size_bytes": size,
        "valid": True,
        "error": None,
    }
