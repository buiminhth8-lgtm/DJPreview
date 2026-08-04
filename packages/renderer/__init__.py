"""音频渲染模块。"""

from packages.renderer.audio_metadata import AudioRenderResult, get_wav_duration_seconds
from packages.renderer.base import AudioRenderer
from packages.renderer.factory import get_audio_renderer

__all__ = ["AudioRenderResult", "AudioRenderer", "get_audio_renderer", "get_wav_duration_seconds"]
