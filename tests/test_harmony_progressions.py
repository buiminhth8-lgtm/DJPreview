"""T19：Roman numeral / cadence / section-aware progression 测试。"""

import random

from packages.music_core.composer.harmony_progressions import (
    build_section_progression,
    cadence_chords,
    select_progression_symbols,
)
from packages.music_core.theory.chords import is_valid_chord_symbol, parse_chord_symbol
from packages.music_core.theory.roman_numerals import roman_to_chord_symbol


def test_roman_major():
    assert roman_to_chord_symbol("I", "C", "major") == "C"
    assert roman_to_chord_symbol("V", "C", "major") == "G"
    assert roman_to_chord_symbol("vi", "C", "major") == "Am"
    assert roman_to_chord_symbol("IV", "C", "major") == "F"
    assert roman_to_chord_symbol("ii", "C", "major") == "Dm"


def test_roman_minor():
    assert roman_to_chord_symbol("i", "A", "minor") == "Am"
    assert roman_to_chord_symbol("V", "A", "minor") in ("E", "E7")
    assert roman_to_chord_symbol("VI", "A", "minor") == "F"
    assert roman_to_chord_symbol("iv", "A", "minor") == "Dm"
    assert roman_to_chord_symbol("VII", "A", "minor") == "G"


def test_roman_extensions_parseable():
    cases = [
        ("Imaj7", "C", "major"),
        ("vi7", "C", "major"),
        ("ii7", "C", "major"),
        ("V7", "C", "major"),
        ("Iadd9", "C", "major"),
        ("ii7", "A", "minor"),
    ]
    for roman, key, mode in cases:
        symbol = roman_to_chord_symbol(roman, key, mode)
        assert is_valid_chord_symbol(symbol), (roman, symbol)
        assert parse_chord_symbol(symbol)


def test_authentic_cadence():
    assert cadence_chords("authentic", "C", "major")[-2:] == ["G7", "C"]
    assert cadence_chords("authentic", "A", "minor")[-2:] == ["E7", "Am"]


def test_half_cadence_ends_on_dominant():
    assert cadence_chords("half", "C", "major")[-1] == "G"
    assert cadence_chords("half", "A", "minor")[-1] == "E"


def test_plagal_cadence():
    assert cadence_chords("plagal", "C", "major") == ["F", "C"]


def test_deceptive_cadence_not_tonic():
    prog = cadence_chords("deceptive", "C", "major")
    assert prog[0] == "G"
    assert prog[-1] != "C"


def test_section_aware_progression():
    key, mode, style = "C", "major", ["pop"]
    verse = build_section_progression("verse", key, mode, style, 8)
    pre = build_section_progression("pre_chorus", key, mode, style, 4)
    chorus = build_section_progression("chorus", key, mode, style, 8)
    bridge = build_section_progression("bridge", key, mode, style, 4)
    outro = build_section_progression("outro", key, mode, style, 4)

    assert len(verse) == 8
    for prog in (verse, pre, chorus, bridge, outro):
        assert all(is_valid_chord_symbol(c) for c in prog)
    assert pre[-1] in ("G", "G7")
    assert chorus[-2:] == ["G7", "C"]
    assert outro[-1] == "C"
    assert bridge != chorus


def test_minor_section_progression_parseable():
    prog = build_section_progression("verse", "D", "minor", ["cinematic"], 8)
    assert all(is_valid_chord_symbol(c) for c in prog)


def test_lo_fi_contains_extended_chord():
    prog = select_progression_symbols(["lo-fi"], "C", "major", random.Random(1))
    assert any("7" in c or "maj7" in c for c in prog)
    assert all(is_valid_chord_symbol(c) for c in prog)
