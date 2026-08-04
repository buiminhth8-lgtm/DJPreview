"""和声质量辅助分析（T19）：轻量指标，不影响生成成功。"""

from __future__ import annotations

from packages.music_core.composer.harmony_progressions import dominant_symbols, tonic_symbol
from packages.music_core.theory.chords import chord_symbol_to_pitches, is_valid_chord_symbol


def _root_pitch_class(symbol: str) -> int | None:
    if not is_valid_chord_symbol(symbol):
        return None
    pitches = chord_symbol_to_pitches(symbol, octave=4)
    return (pitches[0] % 12) if pitches else None


def chord_symbol_validity(progressions: dict[str, list[str]]) -> float:
    """所有生成和弦符号可解析的比例（0-1）。"""
    total = 0
    valid = 0
    for progression in progressions.values():
        for symbol in progression:
            total += 1
            if is_valid_chord_symbol(symbol):
                valid += 1
    return round(valid / total, 3) if total else 1.0


def harmonic_variety_score(progressions: dict[str, list[str]]) -> float:
    """和声多样性 0-1：去重根音数 / 总和弦数。"""
    roots: set[int] = set()
    total = 0
    for progression in progressions.values():
        for symbol in progression:
            root = _root_pitch_class(symbol)
            if root is not None:
                roots.add(root)
                total += 1
    return round(len(roots) / max(1, total), 3)


def cadence_score(progressions: dict[str, list[str]], key: str, mode: str) -> float:
    """终止式得分 0-1：chorus / outro 段落结尾落在主和弦的比例。"""
    tonic_pc = _root_pitch_class(tonic_symbol(key, mode))
    total = 0
    good = 0
    for section, progression in progressions.items():
        if section in ("chorus", "outro", "副歌", "尾奏") and progression:
            last = _root_pitch_class(progression[-1])
            total += 1
            if last is not None and tonic_pc is not None and last == tonic_pc:
                good += 1
    return round(good / total, 3) if total else 0.0


def section_tension_curve_detected(progressions: dict[str, list[str]], key: str, mode: str) -> bool:
    """检测张力曲线：pre_chorus 结尾落在属和弦（V / V7）倾向。"""
    dominants = {_root_pitch_class(s) for s in dominant_symbols(key, mode) if _root_pitch_class(s) is not None}
    for section in ("pre_chorus", "prechorus", "前副歌"):
        progression = progressions.get(section)
        if progression:
            last = _root_pitch_class(progression[-1])
            if last is not None and last in dominants:
                return True
    return False
