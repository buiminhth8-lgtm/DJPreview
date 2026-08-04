"""音频渲染结果与工具。"""

from __future__ import annotations

import wave
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AudioRenderResult:
    """一次音频渲染的结果。"""

    wav_path: Path
    renderer: str
    sample_rate: int
    duration_seconds: float | None
    file_size: int
    warnings: list[str] = field(default_factory=list)


def get_wav_duration_seconds(wav_path: Path) -> float | None:
    """从 WAV 文件头读取时长（秒）；读取失败返回 None。"""
    try:
        with wave.open(str(wav_path), "rb") as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            if rate <= 0:
                return None
            return round(frames / rate, 3)
    except (wave.Error, OSError, EOFError, ValueError):
        return None
