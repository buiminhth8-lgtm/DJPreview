"""和声引擎：把 MusicSpec 的和弦进行映射到每个小节。"""

from __future__ import annotations

from dataclasses import dataclass

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


def build_bar_harmony(music_spec: MusicSpec) -> list[BarHarmony]:
    """把 MusicSpec 的和弦进行展开为逐小节 BarHarmony 列表。

    规则：
    - 每小节必有和弦；
    - 和弦按 progression 循环填充；
    - 总小节数等于 music_spec.length.bars；
    - section 起止小节来自 music_spec.form；
    - 某个 section 缺少 harmony 时使用按调生成的默认进行。
    """
    total = music_spec.length.bars
    progression_by_section: dict[str, list[str]] = {}
    for h in music_spec.harmony:
        progression_by_section.setdefault(h.section, list(h.progression))

    default_prog = _default_progression(music_spec.tonality.key, music_spec.tonality.mode)
    result: list[BarHarmony] = []

    for section in music_spec.form:
        prog = progression_by_section.get(section.id) or default_prog
        if not prog:
            prog = default_prog
        for bar in range(section.start_bar, section.start_bar + section.bars):
            symbol = prog[(bar - section.start_bar) % len(prog)]
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
