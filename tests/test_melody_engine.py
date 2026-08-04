"""T18：MelodyEngine 段落变奏 / chorus lift / outro recall / 调内性测试。"""

from packages.music_core.analysis.melody_analysis import (
    chorus_lift_detected,
    motif_repetition_score,
    outro_theme_recall_detected,
    phrase_balance_score,
)
from packages.music_core.harmony.harmony_engine import build_bar_harmony
from packages.music_core.melody.melody_engine import MelodyEngine
from packages.music_core.theory.scales import get_scale_pitches
from tests.test_harmony_engine import build_spec


def _melody_by_section(music_spec):
    bar_harmony = build_bar_harmony(music_spec)
    notes = MelodyEngine().generate(music_spec, bar_harmony, channel=0)
    sections: dict[str, list] = {}
    for note in notes:
        bar = int(note.start_beat // 4) + 1
        for section in music_spec.form:
            if section.start_bar <= bar < section.start_bar + section.bars:
                sections.setdefault(section.id, []).append(note)
                break
    return notes, sections


def test_verse_and_chorus_have_notes():
    music_spec = build_spec()
    notes, sections = _melody_by_section(music_spec)
    assert notes
    assert sections.get("verse")
    assert sections.get("chorus")


def test_chorus_lift_over_verse():
    music_spec = build_spec()
    _, sections = _melody_by_section(music_spec)
    verse = sections.get("verse", [])
    chorus = sections.get("chorus", [])
    assert verse and chorus
    avg_pitch = lambda ns: sum(n.pitch for n in ns) / len(ns)
    avg_vel = lambda ns: sum(n.velocity for n in ns) / len(ns)
    assert avg_pitch(chorus) >= avg_pitch(verse) - 1.0
    assert avg_vel(chorus) >= avg_vel(verse)
    assert chorus_lift_detected(verse, chorus) is True


def test_outro_recalls_theme():
    music_spec = build_spec()
    _, sections = _melody_by_section(music_spec)
    outro = sections.get("outro", [])
    chorus = sections.get("chorus", [])
    assert outro
    assert outro_theme_recall_detected(chorus, outro) is True
    assert sum(n.velocity for n in outro) / len(outro) <= sum(n.velocity for n in chorus) / len(chorus)


def test_melody_in_scale_and_valid_events():
    music_spec = build_spec()
    notes, _ = _melody_by_section(music_spec)
    scale = get_scale_pitches(music_spec.tonality.key, music_spec.tonality.mode or "major", 4)
    scale_mods = {p % 12 for p in scale}
    assert notes
    assert all(n.pitch % 12 in scale_mods for n in notes)
    assert all(n.duration_beats > 0 for n in notes)
    assert all(n.start_beat >= 0 for n in notes)
    assert all(1 <= n.velocity <= 127 for n in notes)


def test_melody_deterministic_per_seed():
    def flatten(seed):
        spec = build_spec(seed=seed)
        return [(n.pitch, n.start_beat, n.duration_beats, n.velocity) for n in _melody_by_section(spec)[0]]

    assert flatten(42) == flatten(42)
    assert flatten(1) != flatten(2)


def test_analysis_helpers_bounded():
    music_spec = build_spec()
    notes, _ = _melody_by_section(music_spec)
    root = get_scale_pitches(music_spec.tonality.key, music_spec.tonality.mode or "major", 4)[0]
    assert 0.0 <= motif_repetition_score(notes) <= 1.0
    assert 0.0 <= phrase_balance_score(notes, root) <= 1.0
