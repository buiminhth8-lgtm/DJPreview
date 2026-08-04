"""音阶模块：按调式返回 MIDI 音高列表。"""

from __future__ import annotations

from packages.music_core.theory.pitch import normalize_note_name, note_name_to_midi

# 调式 → 相对主音的半音间隔
_SCALE_INTERVALS: dict[str, tuple[int, ...]] = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "ionian": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10),
    "natural_minor": (0, 2, 3, 5, 7, 8, 10),
    "aeolian": (0, 2, 3, 5, 7, 8, 10),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "harmonic_minor": (0, 2, 3, 5, 7, 8, 11),
    "pentatonic": (0, 2, 4, 7, 9),
    "major_pentatonic": (0, 2, 4, 7, 9),
    "minor_pentatonic": (0, 3, 5, 7, 10),
}

SUPPORTED_MODES = frozenset(_SCALE_INTERVALS)


def is_supported_mode(mode: str) -> bool:
    """判断调式是否被支持。"""
    return (mode or "").strip().lower() in SUPPORTED_MODES


def get_scale_pitches(key: str, mode: str, octave: int = 4) -> list[int]:
    """返回指定调式在给定八度的 MIDI 音高列表。

    支持 major / minor / natural_minor / dorian / pentatonic /
    major_pentatonic / minor_pentatonic 等；未知调式回退 major，不崩溃。
    """
    root = note_name_to_midi(normalize_note_name(key), octave)
    mode_lower = (mode or "").strip().lower()
    intervals = _SCALE_INTERVALS.get(mode_lower)
    if intervals is None:
        intervals = _SCALE_INTERVALS["major"]
    return [root + interval for interval in intervals]
