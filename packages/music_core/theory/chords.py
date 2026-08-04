"""和弦解析：和弦符号 → MIDI 音高。"""

from __future__ import annotations

import logging

from packages.music_core.theory.pitch import normalize_note_name, note_name_to_midi

logger = logging.getLogger(__name__)

# 和弦后缀 → 相对根音的半音间隔
_CHORD_INTERVALS: dict[str, tuple[int, ...]] = {
    "": (0, 4, 7),
    "maj": (0, 4, 7),
    "m": (0, 3, 7),
    "min": (0, 3, 7),
    "7": (0, 4, 7, 10),
    "m7": (0, 3, 7, 10),
    "min7": (0, 3, 7, 10),
    "maj7": (0, 4, 7, 11),
    "M7": (0, 4, 7, 11),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
}

# 根音候选（先长后短，确保 C#/Bb 优先于 C/B 匹配）
_ROOT_CANDIDATES = (
    "C#", "DB", "D#", "EB", "F#", "GB", "G#", "AB", "A#", "BB",
    "C", "D", "E", "F", "G", "A", "B",
)

_FALLBACK_ROOT = "C"
_FALLBACK_INTERVALS = (0, 4, 7)


def _match_root(symbol: str) -> str | None:
    """匹配根音；无法识别返回 None。"""
    upper = (symbol or "").strip().upper()
    for root in _ROOT_CANDIDATES:
        if upper.startswith(root):
            return root
    return None


def _split_chord_symbol(symbol: str) -> tuple[str, str]:
    """拆分为 (根音, 后缀)，例如 Dm7 -> ('D', 'm7')。保留原始大小写以区分 m7 / M7。"""
    text = (symbol or "").strip()
    upper = text.upper()
    for root in _ROOT_CANDIDATES:
        if upper.startswith(root):
            return root, text[len(root):]
    return _FALLBACK_ROOT, ""


def _canonical_suffix(suffix: str) -> str:
    """把后缀规范化为字典 key：保留大小写区分 m7（小七）与 M7（大七）。"""
    if suffix == "M7":
        return "maj7"
    if suffix == "M":
        return "maj"
    return suffix.lower()


def is_valid_chord_symbol(symbol: str) -> bool:
    """严格校验和弦符号：根音与后缀都必须被支持（不会悄悄回退 C major）。"""
    root = _match_root(symbol)
    if root is None:
        return False
    suffix = (symbol or "").strip().upper()[len(root):]
    return _canonical_suffix(suffix) in _CHORD_INTERVALS


def parse_chord_symbol(symbol: str, key: str | None = None) -> list[int]:
    """解析和弦符号，返回相对根音的半音间隔；解析失败回退 C major。"""
    root, suffix = _split_chord_symbol(symbol)
    intervals = _CHORD_INTERVALS.get(_canonical_suffix(suffix))
    if intervals is None:
        logger.warning("未知和弦后缀 %r（符号 %r），回退 C major", suffix, symbol)
        return list(_FALLBACK_INTERVALS)
    return list(intervals)


def chord_symbol_to_pitches(symbol: str, octave: int = 4) -> list[int]:
    """将和弦符号转换为 MIDI 音高列表；失败时回退 C major。"""
    root, _ = _split_chord_symbol(symbol)
    try:
        root_midi = note_name_to_midi(normalize_note_name(root), octave)
    except ValueError:
        logger.warning("无法解析根音 %r（符号 %r），回退 C major", root, symbol)
        root_midi = note_name_to_midi("C", octave)
    return [root_midi + interval for interval in parse_chord_symbol(symbol, key=None)]
