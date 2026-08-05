"""表达自动化（T33）：段落能量 → CC7 音量曲线 / CC11 基础表达。"""

from __future__ import annotations

from services.api.schemas.music_spec import MusicSpec
from packages.music_core.composer.events import beats_per_bar

# CC7 volume 范围（1-127；保留空间给混音 volume）
_VOLUME_MIN = 82
_VOLUME_MAX = 116
_CC11_BASE = 100


def _section_energy(music_spec: MusicSpec, section_id: str, default: float = 0.6) -> float:
    for section in music_spec.form:
        if section.id == section_id:
            return max(0.0, min(1.0, section.energy))
    return default


def build_volume_curve(music_spec: MusicSpec) -> list[tuple[float, int]]:
    """按段落小节起点生成 (beat, cc7) 曲线：energy 高 → 音量高，intro/outro 偏低。"""
    bpb = beats_per_bar(music_spec)
    curve: list[tuple[float, int]] = []
    for section in music_spec.form:
        energy = _section_energy(music_spec, section.id)
        section_id = (section.id or "").strip().lower()
        if section_id in ("intro", "outro", "前奏", "尾奏"):
            energy *= 0.75
        value = int(round(_VOLUME_MIN + (_VOLUME_MAX - _VOLUME_MIN) * energy))
        value = max(1, min(127, value))
        beat = round((section.start_bar - 1) * bpb, 3)
        curve.append((beat, value))
    if not curve:
        curve = [(0.0, _VOLUME_MIN)]
    curve.sort(key=lambda item: item[0])
    # 去重同拍
    merged: list[tuple[float, int]] = []
    for beat, value in curve:
        if merged and merged[-1][0] == beat:
            merged[-1] = (beat, value)
        else:
            merged.append((beat, value))
    return merged


def expression_cc11() -> int:
    """基础 expression（CC11），与混音 volume 解耦。"""
    return _CC11_BASE
