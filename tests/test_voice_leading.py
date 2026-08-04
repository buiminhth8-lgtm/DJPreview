"""T22：Voice Leading 测试。"""

from packages.music_core.composer.voice_leading import smooth_voice_leading


def test_voice_leading_output_shape():
    progression = ["C", "G", "Am", "F"]
    voicings = smooth_voice_leading(progression, register=(48, 72), voice_count=3)
    assert len(voicings) == len(progression)
    for voicing in voicings:
        assert len(voicing) == 3
        assert voicing == sorted(voicing)  # 无声部交叉
        assert all(48 <= pitch <= 72 for pitch in voicing)
        assert all(0 <= pitch <= 127 for pitch in voicing)


def test_avg_voice_movement_below_threshold():
    progression = ["C", "G", "Am", "F", "C", "G", "Am", "F"]
    voicings = smooth_voice_leading(progression, register=(48, 72), voice_count=3)
    moves = []
    for prev, curr in zip(voicings, voicings[1:]):
        moves.append(sum(abs(b - a) for a, b in zip(prev, curr)) / len(prev))
    assert sum(moves) / len(moves) <= 9


def test_pitches_are_chord_tones():
    progression = ["C", "G", "Am", "F"]
    voicings = smooth_voice_leading(progression, register=(48, 72), voice_count=3)
    expected = {
        "C": {0, 4, 7},
        "G": {7, 11, 2},
        "Am": {9, 0, 4},
        "F": {5, 9, 0},
    }
    for symbol, voicing in zip(progression, voicings):
        pcs = {pitch % 12 for pitch in voicing}
        assert pcs <= expected[symbol], (symbol, voicing)
