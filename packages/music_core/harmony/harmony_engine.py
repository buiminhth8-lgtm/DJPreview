"""和声引擎：把 MusicSpec 的和弦进行映射到每个小节。"""

from __future__ import annotations

from dataclasses import dataclass

from packages.music_core.composer.harmony_progressions import (
    apply_chord_colors,
    cadence_chords,
    dominant_symbols,
    tonic_symbol,
)
from packages.music_core.theory.chords import chord_symbol_to_pitches
from packages.music_core.theory.pitch import midi_to_note_name
from packages.music_core.theory.scales import get_scale_pitches
from services.api.schemas.music_spec import MusicSpec


@dataclass
class BarHarmony:
    """某一小节的和弦信息。"""

    bar_index: int  # 从 1 开始
    section_id: str
    chord_symbol: str
    chord_pitches: list[int]


def _note_name(pitch: int) -> str:
    """MIDI 音高 → 不带八度的音名，例如 70 -> A#。"""
    name = midi_to_note_name(pitch)
    return name[:-1] if name[-1:].isdigit() else name


def _default_progression(key: str, mode: str) -> list[str]:
    """按调生成默认进行：大调 I-IV-V-vi，小调 i-VI-III-VII。"""
    mode_lower = (mode or "").strip().lower()
    if mode_lower in ("minor", "natural_minor", "aeolian", "minor_pentatonic"):
        scale = get_scale_pitches(key, "minor", octave=4)
        return [
            f"{_note_name(scale[0])}m",
            _note_name(scale[5]),
            _note_name(scale[2]),
            _note_name(scale[6]),
        ]
    scale = get_scale_pitches(key, "major", octave=4)
    return [
        _note_name(scale[0]),
        _note_name(scale[3]),
        _note_name(scale[4]),
        f"{_note_name(scale[5])}m",
    ]


def _ends_with_cadence(progression: list[str], key: str, mode: str) -> bool:
    """粗略判断进行末尾是否已有终止感（主和弦结尾或属和弦倒数第二）。"""
    if len(progression) < 2:
        return True  # 短进行（如 intro / outro 单和弦）不强改
    last = progression[-1]
    prev = progression[-2]
    return last == tonic_symbol(key, mode) or prev in dominant_symbols(key, mode)


def _section_cadence(
    section_id: str,
    key: str,
    mode: str,
    progression: list[str],
) -> list[str] | None:
    """按段落类型返回末尾两小节的终止式和弦；已有终止感或过短则返回 None。"""
    if len(progression) < 2 or _ends_with_cadence(progression, key, mode):
        return None
    sid = (section_id or "").strip().lower()
    if sid in ("chorus", "副歌") or sid in ("outro", "尾奏"):
        return cadence_chords("authentic", key, mode)
    if sid in ("pre_chorus", "prechorus", "前副歌"):
        return cadence_chords("half", key, mode)
    if sid in ("bridge", "桥段"):
        return cadence_chords("deceptive", key, mode)
    if sid in ("verse", "主歌"):
        return cadence_chords("half", key, mode)
    return None


def build_bar_harmony(music_spec: MusicSpec) -> list[BarHarmony]:
    """把 MusicSpec 的和弦进行展开为逐小节 BarHarmony 列表。

    规则：
    - 每小节必有和弦；
    - 和弦按 progression 循环填充；
    - 段落感知终止式（T19）：chorus / outro 结尾 authentic，pre_chorus / verse 结尾 half，
      bridge 结尾 deceptive；lo-fi 等风格会上色（maj7 / m7 / 7）；
    - 总小节数等于 music_spec.length.bars；
    - section 起止小节来自 music_spec.form；
    - 某个 section 缺少 harmony 时使用按调生成的默认进行。
    """
    total = music_spec.length.bars
    progression_by_section: dict[str, list[str]] = {}
    for h in music_spec.harmony:
        progression_by_section.setdefault(h.section, list(h.progression))

    key = music_spec.tonality.key
    mode = music_spec.tonality.mode
    style = list(music_spec.style)
    default_prog = _default_progression(key, mode)
    result: list[BarHarmony] = []

    for section in music_spec.form:
        prog = progression_by_section.get(section.id) or default_prog
        if not prog:
            prog = default_prog
        prog = apply_chord_colors(list(prog), style)
        cadence = _section_cadence(section.id, key, mode, prog)
        bar_count = section.bars
        for i in range(bar_count):
            bar = section.start_bar + i
            if cadence is not None and i >= bar_count - 2:
                symbol = cadence[i - (bar_count - 2)]
            else:
                symbol = prog[i % len(prog)]
            result.append(
                BarHarmony(
                    bar_index=bar,
                    section_id=section.id,
                    chord_symbol=symbol,
                    chord_pitches=chord_symbol_to_pitches(symbol, octave=4),
                )
            )

    # 如果曲式覆盖不足 total（存在缺口），用默认进行补齐
    existing = {bh.bar_index for bh in result}
    if len(existing) < total:
        for bar in range(1, total + 1):
            if bar not in existing:
                symbol = default_prog[(bar - 1) % len(default_prog)]
                result.append(
                    BarHarmony(
                        bar_index=bar,
                        section_id="auto",
                        chord_symbol=symbol,
                        chord_pitches=chord_symbol_to_pitches(symbol, octave=4),
                    )
                )

    result.sort(key=lambda x: x.bar_index)
    return result[:total]
