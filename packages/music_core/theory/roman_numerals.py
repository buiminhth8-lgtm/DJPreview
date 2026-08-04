"""罗马数字 → 和弦符号（T19）：支持 major / minor 常用级数与常见后缀。"""

from __future__ import annotations

from packages.music_core.theory.chords import is_valid_chord_symbol
from packages.music_core.theory.pitch import midi_to_note_name
from packages.music_core.theory.scales import get_scale_pitches

_DEGREES = {"I": 0, "II": 1, "III": 2, "IV": 3, "V": 4, "VI": 5, "VII": 6}

_SUFFIXES = ("maj7", "m7b5", "m7", "sus2", "sus4", "add9", "dim", "m", "7", "6", "°")


def _is_minor_family(mode: str) -> bool:
    return (mode or "").strip().lower() in (
        "minor",
        "natural_minor",
        "aeolian",
        "harmonic_minor",
        "minor_pentatonic",
        "dorian",
    )


def _note_name(pitch: int) -> str:
    name = midi_to_note_name(pitch)
    return name[:-1] if name[-1:].isdigit() else name


def _split_roman(roman: str) -> tuple[str, str]:
    """拆分为 (罗马主体, 后缀)。"""
    token = (roman or "").strip()
    for suffix in sorted(_SUFFIXES, key=len, reverse=True):
        if token.endswith(suffix):
            base = token[: -len(suffix)]
            if base:
                return base, suffix
    return token, ""


def _chord_symbol(root_name: str, base: str, suffix: str) -> str:
    """根据罗马大小写与后缀构造可解析的和弦符号。"""
    lowercase = base[0].islower()
    if suffix == "°":
        return root_name + "dim"
    if suffix == "dim":
        return root_name + "dim"
    if suffix == "m7b5":
        return root_name + "m7b5"
    if suffix == "m7":
        return root_name + "m7"
    if suffix == "maj7":
        return root_name + "maj7"
    if suffix == "7":
        return root_name + ("m7" if lowercase else "7")
    if suffix in ("sus2", "sus4", "add9", "6"):
        return root_name + suffix
    if suffix == "m":
        return root_name + "m"
    return root_name + ("m" if lowercase else "")


def roman_to_chord_symbol(roman: str, key: str, mode: str) -> str:
    """罗马数字 → 具体和弦符号（输出保证可被 chord parser 解析）。

    支持：I / ii / iii / IV / V / vi / vii° / i / ii° / III / iv / v / VI / VII，
    以及后缀 7 / maj7 / m7 / sus2 / sus4 / add9 / 6 / dim / m7b5。
    minor 中 V / V7 使用 harmonic minor 的属和弦（大调三和弦/属七）。
    """
    base, suffix = _split_roman(roman)
    upper = base.upper()
    if upper not in _DEGREES:
        raise ValueError(f"未知罗马数字：{roman!r}")
    degree = _DEGREES[upper]
    scale = get_scale_pitches(
        key,
        "minor" if _is_minor_family(mode) else "major",
        octave=4,
    )
    root_name = _note_name(scale[degree])
    symbol = _chord_symbol(root_name, base, suffix)
    if not is_valid_chord_symbol(symbol):
        raise ValueError(f"罗马数字 {roman!r} 生成非法和弦：{symbol!r}")
    return symbol
