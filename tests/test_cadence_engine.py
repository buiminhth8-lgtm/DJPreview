"""Cadence Engine 测试。"""

from packages.music_core.generation.cadence_engine import suggest_section_cadence
from packages.music_core.theory.chords import parse_chord_symbol
from services.api.schemas.music_spec import HarmonySectionSpec
from tests.test_harmony_engine import build_spec


def test_major_cadence():
    cadence = suggest_section_cadence("chorus", "C", "major", ["pop"], 0.8)
    assert len(cadence) >= 3
    assert cadence[-1] in ("C", "Am") or cadence[-1].endswith("m") is False


def test_minor_cadence():
    cadence = suggest_section_cadence("verse", "D", "minor", ["cinematic"], 0.8)
    assert len(cadence) >= 3
    assert all(parse_chord_symbol(c) for c in cadence)


def test_pentatonic_chinese_no_crash():
    cadence = suggest_section_cadence("verse", "D", "minor_pentatonic", ["chinese"], 0.6)
    assert len(cadence) >= 3
    assert all(parse_chord_symbol(c) for c in cadence)


def test_all_cadences_parseable():
    for mode in ("major", "minor", "pentatonic"):
        cadence = suggest_section_cadence("outro", "C", mode, [], 0.4)
        assert all(parse_chord_symbol(c) for c in cadence)


def test_major_cadence_ends_on_tonic_with_dominant():
    cadence = suggest_section_cadence("chorus", "C", "major", ["pop"], 0.8)
    assert cadence[-1] == "C"
    assert cadence[-2] in ("G7", "G", "F")


def test_minor_cadence_uses_harmonic_dominant():
    cadence = suggest_section_cadence("chorus", "A", "minor", ["cinematic"], 0.9)
    assert cadence[-1] == "Am"
    assert cadence[-2] in ("E7", "E", "Dm")


def test_enhance_cadence_fixes_chorus_ending():
    from packages.music_core.generation.cadence_engine import enhance_harmony_with_cadences

    spec = build_spec()
    spec.harmony = [
        HarmonySectionSpec(section="intro", progression=["Dm"]),
        HarmonySectionSpec(section="verse", progression=["Dm", "Bb", "F", "C"]),
        HarmonySectionSpec(section="chorus", progression=["Dm", "Bb", "F", "A7"]),
        HarmonySectionSpec(section="outro", progression=["Dm"]),
    ]
    enhanced = enhance_harmony_with_cadences(spec, strength=0.8)
    chorus = next(h for h in enhanced.harmony if h.section == "chorus")
    outro = next(h for h in enhanced.harmony if h.section == "outro")
    # D minor：chorus / outro 应落在主和弦 Dm
    assert chorus.progression[-1] == "Dm"
    assert outro.progression[-1] == "Dm"
    assert all(parse_chord_symbol(c) for c in chorus.progression)
