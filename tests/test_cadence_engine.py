"""Cadence Engine 测试。"""

from packages.music_core.generation.cadence_engine import suggest_section_cadence
from packages.music_core.theory.chords import parse_chord_symbol


def test_major_cadence():
    cadence = suggest_section_cadence("chorus", "C", "major", ["pop"], 0.8)
    assert len(cadence) >= 3
    assert cadence[-1] in ("C", "Am") or cadence[-1].endswith("m") is False


def test_minor_cadence():
    cadence = suggest_section_cadence("verse", "D", "minor", ["cinematic"], 0.8)
    assert len(cadence) >= 3
    assert all(parse_chord_symbol(c) for c in cadence)


def test_pentatonic_chinese_no_crash():
    cadence = suggest_section_cadence("verse", "D", "minor_pentatonic", ["chinese"], 0.6)
    assert len(cadence) >= 3
    assert all(parse_chord_symbol(c) for c in cadence)


def test_all_cadences_parseable():
    for mode in ("major", "minor", "pentatonic"):
        cadence = suggest_section_cadence("outro", "C", mode, [], 0.4)
        assert all(parse_chord_symbol(c) for c in cadence)
