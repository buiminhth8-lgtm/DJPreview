"""功能和声进行与终止式库（T19）：段落感知 progression + cadence。"""

from __future__ import annotations

import random

from packages.music_core.theory.chords import is_valid_chord_symbol
from packages.music_core.theory.pitch import midi_to_note_name
from packages.music_core.theory.roman_numerals import roman_to_chord_symbol
from packages.music_core.theory.scales import get_scale_pitches


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


# 终止式模板（roman numeral）
CADENCE_PATTERNS: dict[str, tuple[tuple[str, ...], ...]] = {
    "authentic": (("V7", "I"), ("V", "I")),
    "authentic_minor": (("V7", "i"), ("V", "i")),
    "half": (("ii", "V"), ("IV", "V")),
    "half_minor": (("iv", "V"),),
    "plagal": (("IV", "I"), ("iv", "i")),
    "deceptive": (("V", "vi"), ("V", "VI")),
}


def cadence_chords(cadence_name: str, key: str, mode: str) -> list[str]:
    """按调返回终止式和弦符号（确定性取第一个模板）。"""
    minor = _is_minor_family(mode)
    lookup = cadence_name
    if minor and cadence_name == "authentic":
        lookup = "authentic_minor"
    elif minor and cadence_name == "half":
        lookup = "half_minor"
    patterns = CADENCE_PATTERNS.get(lookup) or CADENCE_PATTERNS.get(cadence_name) or (("V", "I"),)
    return [roman_to_chord_symbol(roman, key, mode) for roman in patterns[0]]


# 常见进行模板（roman numeral，按 style/mode 选择）
PROGRESSION_TEMPLATES: dict[str, tuple[tuple[str, ...], ...]] = {
    "major": (
        ("I", "V", "vi", "IV"),
        ("vi", "IV", "I", "V"),
        ("I", "vi", "IV", "V"),
        ("I", "IV", "V", "I"),
        ("ii", "V", "I"),
        ("I", "IV", "I", "V"),
    ),
    "minor": (
        ("i", "VI", "III", "VII"),
        ("i", "iv", "V", "i"),
        ("i", "VII", "VI", "VII"),
        ("i", "VI", "iv", "V"),
    ),
    "lo_fi": (
        ("Imaj7", "vi7", "ii7", "V7"),
        ("vi7", "IVmaj7", "Imaj7", "V7"),
        ("ii7", "V7", "Imaj7", "Imaj7"),
    ),
    "cinematic": (
        ("i", "VI", "III", "VII"),
        ("i", "iv", "VI", "V"),
        ("Iadd9", "V", "vi", "IV"),
    ),
    "chinese": (
        ("i", "VII", "VI", "VII"),
        ("I", "V", "vi", "IV"),
        ("vi", "IV", "V", "I"),
    ),
}


def _style_pool(style: list[str], mode: str) -> tuple[tuple[str, ...], ...]:
    styles = " ".join(style or []).lower()
    if any(k in styles for k in ("lo-fi", "lofi", "hiphop")):
        return PROGRESSION_TEMPLATES["lo_fi"]
    if "chinese" in styles:
        return PROGRESSION_TEMPLATES["chinese"]
    if "cinematic" in styles or "ambient" in styles:
        return PROGRESSION_TEMPLATES["cinematic"]
    if _is_minor_family(mode):
        return PROGRESSION_TEMPLATES["minor"]
    return PROGRESSION_TEMPLATES["major"]


def select_progression_symbols(
    style: list[str],
    key: str,
    mode: str,
    rng: random.Random | None = None,
) -> list[str]:
    """按风格/调式选择一个进行模板并转为和弦符号。"""
    pool = _style_pool(style, mode)
    idx = 0 if rng is None else rng.randrange(len(pool))
    template = pool[idx % len(pool)]
    return [roman_to_chord_symbol(roman, key, mode) for roman in template]


def tonic_symbol(key: str, mode: str) -> str:
    """返回主和弦符号。"""
    scale = get_scale_pitches(key, "minor" if _is_minor_family(mode) else "major", 4)
    root = _note_name(scale[0])
    return f"{root}m" if _is_minor_family(mode) else root


def dominant_symbols(key: str, mode: str) -> set[str]:
    """返回属和弦候选（V / V7）。"""
    # minor 使用 harmonic minor：V 为大三和弦/属七（升高导音）
    scale_mode = "harmonic_minor" if _is_minor_family(mode) else "major"
    scale = get_scale_pitches(key, scale_mode, 4)
    fifth = _note_name(scale[4])
    return {fifth, fifth + "7"}


def subdominant_symbols(key: str, mode: str) -> set[str]:
    """返回下属和弦候选（IV / iv）。"""
    scale = get_scale_pitches(key, "minor" if _is_minor_family(mode) else "major", 4)
    fourth = _note_name(scale[3])
    return {fourth, fourth + "m" if _is_minor_family(mode) else fourth}


def build_section_progression(
    section_id: str,
    key: str,
    mode: str,
    style: list[str],
    bars: int,
    rng: random.Random | None = None,
) -> list[str]:
    """按段落类型生成 bars 长度的和声进行（含终止式），全部可解析。"""
    bars = max(1, int(bars))
    prog = select_progression_symbols(style, key, mode, rng)
    sid = (section_id or "").strip().lower()
    result: list[str] = []

    if sid in ("intro", "前奏"):
        base = prog[:2] or prog
        result = [base[i % len(base)] for i in range(bars)]
    elif sid in ("pre_chorus", "prechorus", "前副歌"):
        result = [prog[i % len(prog)] for i in range(bars)]
        if bars >= 2:
            result[-2:] = cadence_chords("half", key, mode)
    elif sid in ("chorus", "副歌"):
        result = [prog[i % len(prog)] for i in range(bars)]
        if bars >= 2:
            result[-2:] = cadence_chords("authentic", key, mode)
    elif sid in ("bridge", "桥段"):
        # 对比性进行：换用另一调式池 + deceptive 结尾
        alt_pool = PROGRESSION_TEMPLATES["minor"] if not _is_minor_family(mode) else PROGRESSION_TEMPLATES["major"]
        idx = 0 if rng is None else rng.randrange(len(alt_pool))
        alt_template = alt_pool[idx % len(alt_pool)]
        result = [roman_to_chord_symbol(r, key, mode) for r in alt_template]
        while len(result) < bars:
            result.append(roman_to_chord_symbol(alt_template[len(result) % len(alt_template)], key, mode))
        result = result[:bars]
        if bars >= 2:
            result[-2:] = cadence_chords("deceptive", key, mode)
    elif sid in ("outro", "尾奏"):
        result = [prog[i % len(prog)] for i in range(bars)]
        if bars >= 2:
            result[-2:] = cadence_chords("plagal" if not _is_minor_family(mode) else "authentic", key, mode)
    else:
        result = [prog[i % len(prog)] for i in range(bars)]
        if sid in ("verse", "主歌") and bars >= 2:
            result[-2:] = cadence_chords("half", key, mode)

    return [symbol if is_valid_chord_symbol(symbol) else prog[0] for symbol in result]


def lo_fi_color(symbol: str) -> str:
    """lo-fi 色彩：大三和弦 → maj7，小三和弦 → m7，已带扩展后缀则跳过。"""
    if any(marker in symbol for marker in ("7", "maj", "sus", "add", "6", "dim")):
        return symbol
    if symbol.endswith("m"):
        return symbol + "7"
    return symbol + "maj7"


def apply_chord_colors(progression: list[str], style: list[str]) -> list[str]:
    """按风格给进行上色（保守：只处理可解析的结果）。"""
    styles = " ".join(style or []).lower()
    if not any(k in styles for k in ("lo-fi", "lofi", "hiphop")):
        return progression
    colored: list[str] = []
    for symbol in progression:
        candidate = lo_fi_color(symbol)
        colored.append(candidate if is_valid_chord_symbol(candidate) else symbol)
    return colored
