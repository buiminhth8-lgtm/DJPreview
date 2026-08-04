"""乐理基础模块测试。"""

from packages.music_core.theory.chords import chord_symbol_to_pitches, parse_chord_symbol
from packages.music_core.theory.pitch import midi_to_note_name, normalize_note_name, note_name_to_midi
from packages.music_core.theory.scales import get_scale_pitches


def test_c4_is_midi_60():
    assert note_name_to_midi("C", 4) == 60
    assert midi_to_note_name(60) == "C4"


def test_normalize_note_name():
    assert normalize_note_name("Db") == "C#"
    assert normalize_note_name("Bb") == "A#"


def test_d_minor_scale():
    assert get_scale_pitches("D", "minor", octave=4) == [62, 64, 65, 67, 69, 70, 72]


def test_pentatonic_scale():
    assert get_scale_pitches("C", "pentatonic", octave=4) == [60, 62, 64, 67, 69]


def test_unknown_mode_falls_back_to_major():
    pitches = get_scale_pitches("C", "some_unknown_mode", octave=4)
    assert pitches == [60, 62, 64, 65, 67, 69, 71]


def test_c_major_chord():
    assert parse_chord_symbol("C") == [0, 4, 7]
    assert chord_symbol_to_pitches("C", octave=4) == [60, 64, 67]


def test_dm_chord():
    assert chord_symbol_to_pitches("Dm", octave=4) == [62, 65, 69]


def test_bb_chord():
    assert chord_symbol_to_pitches("Bb", octave=4) == [70, 74, 77]


def test_am7_chord():
    assert chord_symbol_to_pitches("Am7", octave=4) == [69, 72, 76, 79]


def test_c7_and_maj7():
    assert chord_symbol_to_pitches("C7", octave=4) == [60, 64, 67, 70]
    assert chord_symbol_to_pitches("Gmaj7", octave=4) == [67, 71, 74, 78]


def test_unknown_chord_falls_back_to_c_major():
    assert parse_chord_symbol("H???") == [0, 4, 7]
    assert chord_symbol_to_pitches("???", octave=4) == [60, 64, 67]
