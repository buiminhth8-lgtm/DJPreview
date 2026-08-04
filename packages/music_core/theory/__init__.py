"""乐理基础模块。"""

from packages.music_core.theory.chords import chord_symbol_to_pitches, is_valid_chord_symbol, parse_chord_symbol
from packages.music_core.theory.pitch import (
    is_valid_note_name,
    midi_to_note_name,
    normalize_note_name,
    note_name_to_midi,
)
from packages.music_core.theory.scales import SUPPORTED_MODES, get_scale_pitches, is_supported_mode

__all__ = [
    "SUPPORTED_MODES",
    "chord_symbol_to_pitches",
    "get_scale_pitches",
    "is_supported_mode",
    "is_valid_chord_symbol",
    "is_valid_note_name",
    "midi_to_note_name",
    "normalize_note_name",
    "note_name_to_midi",
    "parse_chord_symbol",
]
