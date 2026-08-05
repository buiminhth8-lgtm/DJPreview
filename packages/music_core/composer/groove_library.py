"""Groove 库（T20）：风格 → groove / swing / 段落强度 / fill 规则。"""

from __future__ import annotations

import random

from packages.music_core.composer.drum_models import DrumHit
from packages.music_core.composer.drum_patterns import GROOVE_BUILDERS, build_fill


def style_swing(style: str) -> float:
    """风格默认 swing（0.5=straight；lo-fi/hiphop 更明显）。"""
    if style in ("lo-fi", "hiphop", "lofi_swing", "funk_groove"):
        return 0.62
    return 0.5


def section_intensity(section_id: str, energy: float) -> float:
    """段落鼓组强度基准（0-1）。"""
    base = {
        "intro": 0.25,
        "verse": 0.5,
        "pre_chorus": 0.7,
        "prechorus": 0.7,
        "chorus": 1.0,
        "bridge": 0.45,
        "outro": 0.3,
    }.get((section_id or "").strip().lower(), 0.6)
    return max(0.0, min(1.0, base + (energy - 0.5) * 0.4))


def groove_for(style: str, intensity: float) -> list:
    """按风格生成一小节 groove hits。"""
    builder = GROOVE_BUILDERS.get(style, GROOVE_BUILDERS["pop"])
    return builder(intensity)


def fill_at_section_end(section_id: str, bar_index: int, bar_count: int) -> bool:
    """是否在该小节放置 fill：段落末尾（verse/pre_chorus/bridge/outro）或 chorus 每 8 小节。"""
    sid = (section_id or "").strip().lower()
    if bar_index == bar_count - 1 and sid in (
        "verse",
        "pre_chorus",
        "prechorus",
        "bridge",
        "outro",
        "尾奏",
    ):
        return True
    if sid == "chorus" and bar_index % 8 == 7:
        return True
    return False


def crash_at_section_start(section_id: str, bar_index: int) -> bool:
    """chorus 第一小节第一拍放置 crash。"""
    return (section_id or "").strip().lower() in ("chorus", "副歌") and bar_index == 0


def intro_drum_filter(hits: list, rng: random.Random) -> list:
    """intro：只保留 kick 与踩镲，力度更低。"""
    kept = [h for h in hits if h.note in (36, 42, 44)]
    return [type(h)(time_beats=h.time_beats, duration_beats=h.duration_beats, note=h.note, velocity=max(1, h.velocity - 18), label=h.label) for h in kept]


def bridge_drum_filter(hits: list, rng: random.Random) -> list:
    """bridge：去掉 crash/ride，加入 tom 对比。"""
    kept = [h for h in hits if h.note not in (49, 51)]
    if kept and rng.random() < 0.7:
        kept.append(DrumHit(time_beats=2.5, duration_beats=0.3, note=47, velocity=80, label="tom"))
    return kept


def outro_drum_filter(hits: list, rng: random.Random) -> list:
    """outro：只保留 kick 与轻踩镲。"""
    return [h for h in hits if h.note in (36, 42, 44)]
