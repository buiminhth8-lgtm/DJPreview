"""音频渲染器工厂。"""

from __future__ import annotations

import logging
import os

from packages.renderer.base import AudioRenderer
from packages.renderer.fallback_renderer import FallbackRenderer
from packages.renderer.fluidsynth_renderer import FluidSynthRenderer

logger = logging.getLogger(__name__)


def get_audio_renderer(renderer_name: str | None = None) -> AudioRenderer:
    """根据环境变量 AUDIO_RENDERER 返回渲染器。

    - auto（默认）：优先 FluidSynth，不可用时回退 FallbackRenderer
    - fluidsynth：强制 FluidSynth（不可用时报错）
    - fallback：直接使用开发兜底渲染器
    """
    name = (renderer_name or os.getenv("AUDIO_RENDERER", "") or "auto").strip().lower()
    if name == "fluidsynth":
        return FluidSynthRenderer()
    if name == "fallback":
        return FallbackRenderer()
    if name == "auto":
        fluidsynth = FluidSynthRenderer()
        available, warnings = fluidsynth.is_available()
        if available:
            return fluidsynth
        logger.warning("FluidSynth 不可用（%s），改用 FallbackRenderer", "；".join(warnings))
        return FallbackRenderer()
    raise ValueError(f"未知的 AUDIO_RENDERER：{name!r}（支持 auto、fluidsynth、fallback）")
