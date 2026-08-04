"""Motif Engine 测试。"""

import random

from packages.music_core.generation.generation_context import GenerationContext
from packages.music_core.generation.motif_engine import create_motif, motif_to_note_events, transform_motif
from packages.music_core.theory.scales import get_scale_pitches


def test_create_motif_returns_motif():
    scale = get_scale_pitches("D", "minor", 4)
    chord = [62, 65, 69]
    motif = create_motif(scale, chord, energy=0.7, density=0.6, rng=random.Random(1))
    assert motif.notes
    assert motif.length_beats == 4.0
    assert motif.contour in ("rising", "falling", "arch", "wave", "static")


def test_motif_to_note_events():
    scale = get_scale_pitches("C", "major", 4)
    motif = create_motif(scale, [60, 64, 67], energy=0.7, density=0.6, rng=random.Random(2))
    context = GenerationContext(
        start_beat=0.0,
        root_pitch=60,
        velocity=80,
        channel=0,
        scale_degrees=sorted({p - 60 for p in scale}),
    )
    events = motif_to_note_events(motif, context)
    assert events
    assert all(e.start_beat >= 0 for e in events)
    # 音高都在 C major 内
    scale_mods = {p % 12 for p in scale}
    assert all(e.pitch % 12 in scale_mods for e in events)


def test_same_seed_stable():
    scale = get_scale_pitches("D", "minor", 4)
    m1 = create_motif(scale, [62, 65, 69], 0.7, 0.6, random.Random(7))
    m2 = create_motif(scale, [62, 65, 69], 0.7, 0.6, random.Random(7))
    assert [(n.degree, n.offset_beats, n.duration_beats) for n in m1.notes] == [
        (n.degree, n.offset_beats, n.duration_beats) for n in m2.notes
    ]


def test_intensify_increases_density():
    scale = get_scale_pitches("C", "major", 4)
    motif = create_motif(scale, [60, 64, 67], 0.7, 0.6, random.Random(3))
    intensified = transform_motif(motif, "intensify", random.Random(4))
    assert intensified.density >= motif.density


def test_simplify_reduces_notes():
    scale = get_scale_pitches("C", "major", 4)
    motif = create_motif(scale, [60, 64, 67], 0.9, 0.9, random.Random(5))
    simplified = transform_motif(motif, "simplify", random.Random(6))
    assert len(simplified.notes) <= len(motif.notes)
