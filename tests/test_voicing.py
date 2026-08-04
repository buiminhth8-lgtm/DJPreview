"""T22：和弦 Voicing 测试。"""

from packages.music_core.composer.voicing import build_chord_voicing


def test_c_major_voicing():
    voicing = build_chord_voicing("C", register=(48, 72), voice_count=3)
    assert len(voicing) == 3
    assert voicing == sorted(voicing)
    assert all(48 <= pitch <= 72 for pitch in voicing)
    pcs = {pitch % 12 for pitch in voicing}
    assert pcs <= {0, 4, 7}


def test_am7_voicing():
    voicing = build_chord_voicing("Am7", register=(48, 72), voice_count=4)
    assert len(voicing) >= 3
    pcs = {pitch % 12 for pitch in voicing}
    assert 9 in pcs  # A
    assert 0 in pcs  # C
    assert 4 in pcs  # E
    assert 7 in pcs  # G


def test_csus4_no_third():
    voicing = build_chord_voicing("Csus4", register=(48, 72), voice_count=3)
    pcs = {pitch % 12 for pitch in voicing}
    assert 0 in pcs
    assert 5 in pcs  # F
    assert 4 not in pcs  # E


def test_cadd9_contains_ninth():
    voicing = build_chord_voicing("Cadd9", register=(48, 72), voice_count=3)
    pcs = {pitch % 12 for pitch in voicing}
    assert 2 in pcs  # D


def test_invalid_chord_no_crash():
    voicing = build_chord_voicing("H??", register=(48, 72), voice_count=3)
    assert voicing
    assert all(48 <= pitch <= 72 for pitch in voicing)
    assert voicing == sorted(voicing)


def test_previous_voicing_used():
    previous = [48, 52, 55]
    voicing = build_chord_voicing("G", register=(48, 72), voice_count=3, previous_voicing=previous)
    assert len(voicing) == 3
    assert all(48 <= pitch <= 72 for pitch in voicing)
