"""FluidSynth 可用性检测与 SoundFont 文件校验（T39-B）。

- detect_fluidsynth()：检测系统 FluidSynth 是否可用（env → PATH → --version）。
- validate_soundfont_file()：校验 SoundFont 文件存在 / 可读 / 格式 / RIFF 头。
这些函数是纯诊断工具，不改变渲染核心逻辑；不可用时由调用方决定 fallback。
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

SUPPORTED_EXTENSIONS = (".sf2", ".sf3", ".sfz")


def detect_fluidsynth() -> dict:
    """检测 FluidSynth 是否可用，返回结构化状态。

    优先读取环境变量 FLUIDSYNTH_BIN / FLUIDSYNTH_PATH，其次查找 PATH。
    执行 `fluidsynth --version` 验证可执行，捕获 not found / 权限 / 超时 / 非零退出。
    不会抛出异常：FluidSynth 不可用时返回 available=False。
    """
    binary = os.getenv("FLUIDSYNTH_BIN", "").strip() or os.getenv("FLUIDSYNTH_PATH", "").strip() or ""
    if binary:
        # 值是完整路径：要求文件存在
        if Path(binary).exists():
            resolved = str(Path(binary).resolve())
        else:
            # 值是裸命令名（如 "fluidsynth"）：交给 PATH 查找
            resolved = shutil.which(binary)
            if not resolved:
                return {
                    "available": False,
                    "binary": binary,
                    "version": None,
                    "error": f"FLUIDSYNTH_BIN 指定 {binary!r} 但 PATH 中找不到该命令",
                }
        binary = resolved
    else:
        binary = shutil.which("fluidsynth") or shutil.which("fluidsynth.exe")
        if not binary:
            return {
                "available": False,
                "binary": None,
                "version": None,
                "error": "fluidsynth not found in PATH",
            }

    try:
        proc = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "available": False,
            "binary": binary,
            "version": None,
            "error": f"fluidsynth --version 超时（{exc}）",
        }
    except (OSError, PermissionError) as exc:
        return {
            "available": False,
            "binary": binary,
            "version": None,
            "error": f"无法执行 fluidsynth：{exc}",
        }

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        return {
            "available": False,
            "binary": binary,
            "version": None,
            "error": f"fluidsynth --version 退出码 {proc.returncode}：{detail[-1] if detail else 'unknown'}",
        }

    first_line = (proc.stdout or proc.stderr or "").strip().splitlines()
    version = first_line[0].strip() if first_line else None
    return {
        "available": True,
        "binary": binary,
        "version": version,
        "error": None,
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
