"""T19：Chord Parser 扩展和弦测试。"""

import pytest

from packages.music_core.theory.chords import (
    chord_symbol_to_pitches,
    is_valid_chord_symbol,
    parse_chord_symbol,
)

PARSABLE = [
    "C",
    "Cm",
    "Cmaj7",
    "C7",
    "Cm7",
    "Csus2",
    "Csus4",
    "Cadd9",
    "C6",
    "Am",
    "Am7",
    "Fmaj7",
    "G7",
    "Cdim",
    "Cm7b5",
]


@pytest.mark.parametrize("symbol", PARSABLE)
def test_parseable(symbol):
    assert is_valid_chord_symbol(symbol)
    assert parse_chord_symbol(symbol)
    assert chord_symbol_to_pitches(symbol, octave=4)


def test_sus4_no_third_contains_fourth():
    pcs = {p % 12 for p in chord_symbol_to_pitches("Csus4", octave=4)}
    assert 0 in pcs  # C
    assert 5 in pcs  # F
    assert 4 not in pcs  # E（三音被替换）


def test_add9_contains_ninth():
    pcs = {p % 12 for p in chord_symbol_to_pitches("Cadd9", octave=4)}
    assert 2 in pcs  # D
    assert {0, 4, 7} <= pcs


def test_maj7_contains_major_seventh():
    pcs = {p % 12 for p in chord_symbol_to_pitches("Cmaj7", octave=4)}
    assert 11 in pcs  # B
    assert 10 not in pcs


def test_dominant7_contains_flat_seventh():
    pcs = {p % 12 for p in chord_symbol_to_pitches("C7", octave=4)}
    assert 10 in pcs  # Bb
    assert 11 not in pcs


def test_m7_vs_maj7_distinguished():
    m7 = {p % 12 for p in chord_symbol_to_pitches("Cm7", octave=4)}
    maj7 = {p % 12 for p in chord_symbol_to_pitches("Cmaj7", octave=4)}
    assert 3 in m7
    assert 10 in m7
    assert 4 in maj7
    assert 11 in maj7
