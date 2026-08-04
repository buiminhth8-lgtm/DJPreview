"""音高与 MIDI 编号转换工具。"""

from __future__ import annotations

# 音名 → 半音（升号、降号均支持）
_NOTE_TO_SEMITONE: dict[str, int] = {
    "C": 0,
    "C#": 1,
    "DB": 1,
    "D": 2,
    "D#": 3,
    "EB": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "GB": 6,
    "G": 7,
    "G#": 8,
    "AB": 8,
    "A": 9,
    "A#": 10,
    "BB": 10,
    "B": 11,
}

# 降号 → 升号规范化
_FLAT_TO_SHARP: dict[str, str] = {
    "DB": "C#",
    "EB": "D#",
    "GB": "F#",
    "AB": "G#",
    "BB": "A#",
}

# MIDI 编号 → 规范音名
_MIDI_TO_NAME: list[str] = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def normalize_note_name(note: str) -> str:
    """把降号音名规范化为升号形式，例如 Db -> C#、Bb -> A#。"""
    cleaned = (note or "").strip().upper()
    return _FLAT_TO_SHARP.get(cleaned, cleaned)


def is_valid_note_name(note: str) -> bool:
    """判断音名是否被支持（C/C#/Db/D/.../B）。"""
    return normalize_note_name(note) in _NOTE_TO_SEMITONE


def note_name_to_midi(note: str, octave: int) -> int:
    """将音名与八度转换为 MIDI 编号，例如 C4 -> 60。"""
    name = normalize_note_name(note)
    if name not in _NOTE_TO_SEMITONE:
        raise ValueError(f"不支持的音名：{note!r}")
    return (octave + 1) * 12 + _NOTE_TO_SEMITONE[name]


def midi_to_note_name(midi: int) -> str:
    """将 MIDI 编号转换为音名 + 八度，例如 60 -> C4。"""
    if not 0 <= midi <= 127:
        raise ValueError(f"MIDI 编号超出范围：{midi}")
    name = _MIDI_TO_NAME[midi % 12]
    octave = midi // 12 - 1
    return f"{name}{octave}"
