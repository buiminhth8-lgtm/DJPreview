"""T18：Question / Answer phrase 构建测试。"""

import random

from packages.music_core.composer.phrase_builder import (
    build_answer_phrase,
    build_question_phrase,
    phrase_to_motif,
)


def _context():
    # C major：scale degrees 0,2,4,5,7,9,11；和弦音 0,4,7
    return [0, 2, 4, 5, 7, 9, 11], [0, 4, 7]


def test_question_and_answer_not_empty():
    scale, chord = _context()
    rng = random.Random(1)
    assert build_question_phrase(scale, chord, rng, 4.0)
    assert build_answer_phrase(scale, chord, rng, 4.0)


def test_answer_ending_more_stable_than_question():
    scale, chord = _context()
    stable = {0, 4, 7}
    for seed in range(5):
        rng = random.Random(seed)
        question = build_question_phrase(scale, chord, rng, 4.0)
        answer = build_answer_phrase(scale, chord, rng, 4.0)
        assert question[-1].scale_degree not in stable
        assert answer[-1].scale_degree in stable


def test_phrase_notes_valid():
    scale, chord = _context()
    rng = random.Random(2)
    phrases = [build_question_phrase(scale, chord, rng, 4.0), build_answer_phrase(scale, chord, rng, 4.0)]
    for phrase in phrases:
        for note in phrase:
            assert note.duration_beats > 0
            assert 0.0 <= note.offset_beats < 4.0
            assert note.offset_beats + note.duration_beats <= 4.0 + 1e-6
            assert 1 <= note.velocity <= 127


def test_phrase_to_motif():
    scale, chord = _context()
    phrase = build_answer_phrase(scale, chord, random.Random(3), 4.0)
    motif = phrase_to_motif(phrase, 4.0)
    assert motif.notes
    assert motif.length_beats == 4.0
    assert motif.contour in ("ascending", "descending", "arch", "wave", "static")
