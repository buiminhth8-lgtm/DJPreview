"""音频渲染统一抽象接口。"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from packages.renderer.audio_metadata import AudioRenderResult


@runtime_checkable
class AudioRenderer(Protocol):
    """所有音频渲染器必须实现的接口。"""

    name: str

    def render_wav(
        self,
        midi_path: Path,
        wav_path: Path,
        *,
        sample_rate: int = 44100,
        gain: float = 0.6,
        soundfont_path: Path | str | None = None,
    ) -> AudioRenderResult:
        """把 MIDI 文件渲染为 WAV 文件，返回渲染结果。

        soundfont_path 为可选音源路径；fallback 渲染器忽略该参数，
        FluidSynth 渲染器使用指定音源（未指定时用默认配置）。
        """
