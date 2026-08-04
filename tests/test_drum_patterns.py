"""T20：鼓组 groove 模式测试。"""

import random

from packages.music_core.composer.drum_patterns import (
    GM_DRUM_NOTES,
    build_fill,
    cinematic_groove,
    lo_fi_groove,
    pop_groove,
    rock_groove,
)


def _notes(hits):
    return {h.note for h in hits}


def test_pop_groove_has_kick_snare_hat():
    hits = pop_groove(0.6)
    notes = _notes(hits)
    assert GM_DRUM_NOTES["kick"] in notes
    assert GM_DRUM_NOTES["snare"] in notes
    assert GM_DRUM_NOTES["closed_hat"] in notes


def test_rock_groove_has_kick_snare_hat():
    hits = rock_groove(0.6)
    notes = _notes(hits)
    assert GM_DRUM_NOTES["kick"] in notes
    assert GM_DRUM_NOTES["snare"] in notes
    assert GM_DRUM_NOTES["closed_hat"] in notes


def test_lo_fi_groove_has_ghost_note():
    hits = lo_fi_groove(0.6)
    ghosts = [h for h in hits if h.velocity < 50]
    assert ghosts
    assert all(25 <= h.velocity <= 45 for h in ghosts)


def test_cinematic_sparser_than_pop():
    assert len(cinematic_groove(0.6)) < len(pop_groove(0.6))


def test_all_hits_valid():
    for groove in (pop_groove(0.6), rock_groove(0.6), lo_fi_groove(0.6), cinematic_groove(0.6)):
        for hit in groove:
            assert 1 <= hit.velocity <= 127
            assert hit.time_beats >= 0
            assert hit.time_beats < 4.0
            assert hit.duration_beats > 0
            assert 0 <= hit.note <= 127


def test_fill_not_overflow():
    hits = build_fill("pop", random.Random(1))
    assert hits
    assert all(3.0 <= h.time_beats < 4.0 for h in hits)
    assert all(1 <= h.velocity <= 127 for h in hits)
