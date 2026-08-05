"""Cadence Engine：乐句终止式建议与和声增强。"""

from __future__ import annotations

from packages.music_core.composer.harmony_progressions import cadence_chords
from packages.music_core.theory.chords import parse_chord_symbol
from packages.music_core.theory.pitch import midi_to_note_name
from packages.music_core.theory.scales import get_scale_pitches
from services.api.schemas.music_spec import MusicSpec


def _note_name(pitch: int) -> str:
    """MIDI 音高 → 不带八度的音名（升号）。"""
    name = midi_to_note_name(pitch)
    return name[:-1] if name[-1:].isdigit() else name


def _is_minor_family(mode: str) -> bool:
    return mode.lower() in ("minor", "natural_minor", "aeolian", "minor_pentatonic", "dorian")


def _is_pentatonic(mode: str, style: list[str]) -> bool:
    return mode.lower() in ("pentatonic", "major_pentatonic", "minor_pentatonic") or "chinese" in " ".join(style).lower()


def suggest_section_cadence(
    section_id: str,
    key: str,
    mode: str,
    style: list[str],
    energy: float,
) -> list[str]:
    """根据调式与风格建议终止式（返回可解析的和弦符号列表）。"""
    style_text = " ".join(style).lower()
    if _is_pentatonic(mode, style):
        # 中国风五声：i-VII-VI-i（按小调音阶取音名）
        scale = get_scale_pitches(key, "minor" if _is_minor_family(mode) else "major", octave=4)
        if _is_minor_family(mode):
            i, vi, vii = scale[0], scale[5], scale[6]
            return [f"{_note_name(i)}m", _note_name(vii), _note_name(vi), f"{_note_name(i)}m"]
        return [_note_name(scale[0]), f"{_note_name(scale[5])}m", _note_name(scale[3]), _note_name(scale[0])]

    if _is_minor_family(mode):
        if "cinematic" in style_text or energy >= 0.8:
            # 电影感：iv → V7 → i（属七强调）
            return [*cadence_chords("half_minor", key, mode), *cadence_chords("authentic", key, mode)[-2:]]
        # 常规 minor：iv → V7 → i
        return [*cadence_chords("half_minor", key, mode), *cadence_chords("authentic", key, mode)[-2:]]

    if "pop" in style_text or "ballad" in style_text:
        return [*cadence_chords("plagal", key, mode), *cadence_chords("authentic", key, mode)[-2:]]
    return [*cadence_chords("half", key, mode), *cadence_chords("authentic", key, mode)[-2:]]


def _cadence_like(progression: list[str], key: str, mode: str, style: list[str], energy: float) -> bool:
    """粗略判断末尾是否已有终止感（末和弦为主和弦且倒数第二为属/下属方向）。"""
    if len(progression) < 2:
        return False
    last = progression[-1]
    prev = progression[-2]
    tonic = cadence_chords("authentic", key, mode)[-1]
    if last != tonic:
        return False
    dominants = set(cadence_chords("authentic", key, mode))
    plagal = cadence_chords("plagal", key, mode)
    return prev in dominants or prev in plagal


_CADENCE_SECTIONS = {"chorus", "final_chorus", "outro", "副歌", "尾奏"}


def enhance_harmony_with_cadences(music_spec: MusicSpec, strength: float = 0.6) -> MusicSpec:
    """为 chorus / outro 等段落自动补明确终止式；其余段落仅补强（不强改）。"""
    spec = music_spec.model_copy(deep=True)
    key, mode = spec.tonality.key, spec.tonality.mode
    style = list(spec.style)
    for harmony in spec.harmony:
        progression = list(harmony.progression)
        energy = next((s.energy for s in spec.form if s.id == harmony.section), 0.6)
        cadence = suggest_section_cadence(harmony.section, key, mode, style, energy)
        section = (harmony.section or "").strip().lower()
        if section in _CADENCE_SECTIONS:
            # chorus / outro：结尾必须落回主和弦
            ending = cadence[-2:]
            if len(progression) == 1:
                replacement = list(ending)
            elif len(progression) >= 2:
                replacement = progression[:-2] + list(ending)
            else:
                continue
        elif len(progression) >= 4 and not _cadence_like(progression, key, mode, style, energy):
            # 其他段落：保持原样或仅补强，不强行 authentic
            replacement = progression[:-2] + list(cadence[-2:])
        else:
            continue
        if replacement and all(parse_chord_symbol(c) for c in replacement):
            harmony.progression = replacement
    return spec
