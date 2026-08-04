"""T18：melodic motif / theme 生成与渲染测试。"""

import random

from packages.music_core.composer.melodic_theme import (
    MelodicMotif,
    generate_motif,
    motif_to_note_events,
    sparsify_motif,
    variant_motif,
)
from packages.music_core.theory.scales import get_scale_pitches


def _c_major() -> tuple[list[int], list[int]]:
    scale = get_scale_pitches("C", "major", 4)
    return scale, [60, 64, 67]


def test_generate_motif_not_empty_and_length_ok():
    scale, chord = _c_major()
    motif = generate_motif(scale, chord, energy=0.7, density=0.6, rng=random.Random(1))
    assert isinstance(motif, MelodicMotif)
    assert motif.notes
    assert 1.0 <= motif.length_beats <= 8.0
    assert motif.contour in ("ascending", "descending", "arch", "wave", "static")


def test_motif_note_durations_positive_and_within_length():
    scale, chord = _c_major()
    motif = generate_motif(scale, chord, energy=0.8, density=0.8, rng=random.Random(2))
    for note in motif.notes:
        assert note.duration_beats > 0
        assert note.offset_beats >= 0
        assert note.offset_beats + note.duration_beats <= motif.length_beats + 1e-6


def test_motif_scale_degrees_reasonable():
    scale, _ = _c_major()
    root = scale[0]
    scale_mods = {p % 12 for p in scale}
    motif = generate_motif(scale, [60, 64, 67], energy=0.7, density=0.6, rng=random.Random(3))
    for note in motif.notes:
        assert (root + note.scale_degree) % 12 in scale_mods


def test_motif_two_bars():
    scale, chord = _c_major()
    motif = generate_motif(scale, chord, energy=0.7, density=0.5, rng=random.Random(4), length_bars=2, beats_per_bar=4)
    assert motif.length_beats == 8.0
    assert all(n.offset_beats < 8.0 for n in motif.notes)


def test_motif_same_seed_stable():
    scale, chord = _c_major()
    m1 = generate_motif(scale, chord, 0.7, 0.6, random.Random(7))
    m2 = generate_motif(scale, chord, 0.7, 0.6, random.Random(7))
    assert [(n.scale_degree, n.offset_beats, n.duration_beats) for n in m1.notes] == [
        (n.scale_degree, n.offset_beats, n.duration_beats) for n in m2.notes
    ]


def test_variant_motif_keeps_notes():
    scale, chord = _c_major()
    motif = generate_motif(scale, chord, 0.7, 0.6, random.Random(5))
    intensified = variant_motif(motif, "intensify", random.Random(6))
    assert intensified.notes
    assert all(n.duration_beats > 0 for n in intensified.notes)
    simplified = variant_motif(motif, "simplify", random.Random(8))
    assert len(simplified.notes) <= len(motif.notes)


def test_sparsify_keeps_strong_beats():
    scale, chord = _c_major()
    motif = generate_motif(scale, chord, 0.9, 0.9, random.Random(9))
    sparse = sparsify_motif(motif, random.Random(10), keep_ratio=0.2)
    assert sparse.notes
    assert any(n.offset_beats % 1 == 0 for n in sparse.notes)


def test_motif_to_note_events_in_scale():
    scale, chord = _c_major()
    root = scale[0]
    scale_degrees = sorted({p - root for p in scale})
    motif = generate_motif(scale, chord, 0.7, 0.6, random.Random(11))
    events = motif_to_note_events(
        motif,
        start_beat=0.0,
        root_pitch=root,
        scale_degrees=scale_degrees,
        velocity_base=80,
        channel=0,
        pitch_min=55,
        pitch_max=88,
    )
    assert events
    scale_mods = {p % 12 for p in scale}
    assert all(e.pitch % 12 in scale_mods for e in events)
    assert all(e.start_beat >= 0 and e.duration_beats > 0 for e in events)
    assert all(1 <= e.velocity <= 127 for e in events)
