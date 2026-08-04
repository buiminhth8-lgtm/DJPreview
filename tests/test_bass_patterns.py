"""T21：贝斯 groove 模式与工具测试。"""

import random

from packages.music_core.composer.bass_patterns import (
    BASS_MAX,
    BASS_MIN,
    bass_style_swing,
    build_approach_note,
    choose_passing_tone,
    cinematic_bass,
    get_bass_chord_tones,
    get_chord_root_pitch,
    implied_kick_positions,
    lo_fi_bass,
    pop_bass,
    rock_bass,
)


def test_chord_root_pitch_in_bass_range():
    assert get_chord_root_pitch("C") == 36
    assert get_chord_root_pitch("F") == 41
    assert get_chord_root_pitch("G7") == 43


def test_bass_chord_tones():
    tones = get_bass_chord_tones("Cmaj7")
    pcs = {p % 12 for p in tones}
    assert 0 in pcs
    assert 11 in pcs  # maj7 的 B


def test_pop_has_multiple_role_classes():
    hits = pop_bass(36, 43, 48, 1.0, random.Random(1))
    assert len({h.role for h in hits}) >= 2
    pcs = {h.pitch % 12 for h in hits}
    assert 0 in pcs  # root/octave
    assert 7 in pcs  # fifth


def test_rock_has_eighth_note_density():
    hits = rock_bass(36, 43, 48, 1.0, random.Random(1))
    assert len(hits) >= 6


def test_lo_fi_syncopated_or_swing():
    hits = lo_fi_bass(36, 43, 48, 0.6, random.Random(2))
    times = {h.time_beats for h in hits}
    syncopated = any(t % 1.0 == 0.5 or t == 3.75 for t in times)
    assert syncopated or bass_style_swing("lo-fi") > 0.5


def test_cinematic_sparser_than_rock():
    sparse = len(cinematic_bass(36, 43, 48, 0.6, random.Random(3)))
    dense = len(rock_bass(36, 43, 48, 0.6, random.Random(4)))
    assert sparse < dense


def test_all_bass_notes_valid():
    for groove in (
        pop_bass(36, 43, 48, 1.0, random.Random(1)),
        rock_bass(36, 43, 48, 1.0, random.Random(2)),
        lo_fi_bass(36, 43, 48, 0.6, random.Random(3)),
        cinematic_bass(36, 43, 48, 0.6, random.Random(4)),
    ):
        for note in groove:
            assert 1 <= note.velocity <= 127
            assert BASS_MIN <= note.pitch <= BASS_MAX
            assert note.duration_beats > 0
            assert note.time_beats >= 0


def test_passing_and_approach_in_scale():
    scale = {36, 38, 40, 41, 43, 45, 47, 48, 50, 52}
    passing = choose_passing_tone(36, 43, scale)
    assert passing in scale
    approach = build_approach_note(41, scale)
    assert approach is not None
    assert approach < 41


def test_implied_kicks():
    assert implied_kick_positions("pop") == [0.0, 2.0]
    assert 0.0 in implied_kick_positions("rock")
