"""Cadence Engine：乐句终止式建议与和声增强。"""

from __future__ import annotations

from packages.music_core.theory.chords import chord_symbol_to_pitches, parse_chord_symbol
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
        scale = get_scale_pitches(key, "minor", octave=4)
        i, iv, v, vi, vii = scale[0], scale[3], scale[4], scale[5], scale[6]
        if "cinematic" in style_text or energy >= 0.8:
            return [_note_name(vi), _note_name(vii), f"{_note_name(i)}m"]
        return [f"{_note_name(iv)}m", _note_name(v), f"{_note_name(i)}m"]

    scale = get_scale_pitches(key, "major", octave=4)
    i, ii, iv, v, vi = scale[0], scale[1], scale[3], scale[4], scale[5]
    if "pop" in style_text or "ballad" in style_text:
        return [_note_name(iv), _note_name(v), _note_name(i)]
    return [f"{_note_name(ii)}m", _note_name(v), _note_name(i)]


def _cadence_like(progression: list[str], key: str, mode: str, style: list[str], energy: float) -> bool:
    """粗略判断末尾是否已有终止感（末和弦为主和弦且倒数第二为属/下属方向）。"""
    if len(progression) < 2:
        return False
    cadence = suggest_section_cadence("x", key, mode, style, energy)
    if not cadence:
        return False
    return progression[-1] == cadence[-1] and progression[-2] in (cadence[-3:-1] or [cadence[-2]])


def enhance_harmony_with_cadences(music_spec: MusicSpec, strength: float = 0.6) -> MusicSpec:
    """为每个段落末尾 2-4 小节补强终止式（不强制覆盖复杂进行）。"""
    spec = music_spec.model_copy(deep=True)
    key, mode = spec.tonality.key, spec.tonality.mode
    style = list(spec.style)
    for harmony in spec.harmony:
        progression = list(harmony.progression)
        energy = next((s.energy for s in spec.form if s.id == harmony.section), 0.6)
        if len(progression) >= 4 and not _cadence_like(progression, key, mode, style, energy):
            cadence = suggest_section_cadence(harmony.section, key, mode, style, energy)
            # 替换最后 2 个和弦为终止式（保持长度兼容）
            replacement = progression[:-2] + cadence[-2:]
            if replacement and all(parse_chord_symbol(c) for c in replacement):
                harmony.progression = replacement
    return spec
