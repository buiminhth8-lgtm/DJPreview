"""质量检查与自动优化测试。"""

from packages.music_core.analysis.melody_analysis import (
    chorus_lift_detected,
    motif_repetition_score,
    outro_theme_recall_detected,
    phrase_balance_score,
)
from packages.music_core.analysis.quality_checker import check_arrangement_quality
from packages.music_core.optimization.arrangement_optimizer import optimize_arrangement
from packages.music_core.validation.spec_validator import validate_music_spec
from tests.test_harmony_engine import build_spec


def test_normal_spec_gets_report():
    report = check_arrangement_quality(build_spec())
    assert 0 <= report.score <= 100
    assert report.level in ("excellent", "good", "fair", "poor")
    assert report.summary


def test_empty_tracks_produce_error():
    spec = build_spec()
    spec.tracks = []
    report = check_arrangement_quality(spec)
    assert any(i.severity == "error" for i in report.issues)


def test_missing_harmony_produces_warning():
    spec = build_spec()
    spec.harmony = []
    report = check_arrangement_quality(spec)
    assert any(i.category == "harmony" and i.severity == "warning" for i in report.issues)


def test_score_in_range():
    assert 0 <= check_arrangement_quality(build_spec()).score <= 100


def test_melody_analysis_helpers():
    """T18：轻量旋律分析辅助函数可运行且结果有界。"""
    spec = build_spec()
    from packages.music_core.composer.music_composer import compose_music
    from packages.music_core.harmony.harmony_engine import build_bar_harmony
    from packages.music_core.melody.melody_engine import MelodyEngine
    from packages.music_core.theory.scales import get_scale_pitches

    bar_harmony = build_bar_harmony(spec)
    notes = MelodyEngine().generate(spec, bar_harmony, channel=0)
    root = get_scale_pitches(spec.tonality.key, spec.tonality.mode or "major", 4)[0]

    assert 0.0 <= motif_repetition_score(notes) <= 1.0
    assert 0.0 <= phrase_balance_score(notes, root) <= 1.0

    sections: dict[str, list] = {}
    for note in notes:
        bar = int(note.start_beat // 4) + 1
        for section in spec.form:
            if section.start_bar <= bar < section.start_bar + section.bars:
                sections.setdefault(section.id, []).append(note)
                break
    if sections.get("verse") and sections.get("chorus"):
        assert isinstance(chorus_lift_detected(sections["verse"], sections["chorus"]), bool)
    if sections.get("outro") and sections.get("chorus"):
        assert isinstance(outro_theme_recall_detected(sections["chorus"], sections["outro"]), bool)
    assert 0 <= check_arrangement_quality(build_spec()).score <= 100


def test_harmony_analysis_helpers():
    """T19：轻量和声分析辅助函数可运行且结果有界。"""
    from packages.music_core.analysis.harmony_analysis import (
        cadence_score,
        chord_symbol_validity,
        harmonic_variety_score,
        section_tension_curve_detected,
    )

    progressions = {
        "verse": ["Dm", "Bb", "Gm", "A"],
        "pre_chorus": ["Bb", "Gm", "A"],
        "chorus": ["Dm", "Bb", "F", "C", "A7", "Dm"],
        "bridge": ["Cm", "A", "G", "Am"],
        "outro": ["Dm"],
    }
    assert chord_symbol_validity(progressions) == 1.0
    assert 0.0 <= harmonic_variety_score(progressions) <= 1.0
    assert cadence_score(progressions, "D", "minor") == 1.0
    assert section_tension_curve_detected(progressions, "D", "minor") is True


def test_rhythm_analysis_helpers():
    """T20：轻量鼓组/节奏分析辅助函数可运行且结果有界。"""
    from packages.music_core.analysis.rhythm_analysis import (
        chorus_intensity_lift_detected,
        drum_density_score,
        section_fill_detected,
        swing_feel_detected,
        velocity_variation_score,
    )
    from packages.music_core.composer.music_composer import compose_music

    spec = build_spec()
    result = compose_music(spec)
    drums = next(t for t in result.tracks if t.role == "drums").notes
    assert drum_density_score(drums) > 0
    assert 0.0 <= velocity_variation_score(drums) <= 1.0
    assert isinstance(section_fill_detected(drums), bool)
    assert isinstance(swing_feel_detected(drums), bool)

    sections: dict[str, list] = {}
    for note in drums:
        bar = int(note.start_beat // 4) + 1
        for section in spec.form:
            if section.start_bar <= bar < section.start_bar + section.bars:
                sections.setdefault(section.id, []).append(note)
                break
    if sections.get("verse") and sections.get("chorus"):
        assert isinstance(
            chorus_intensity_lift_detected(sections["verse"], sections["chorus"]),
            bool,
        )


def test_optimizer_fixes_missing_melody_and_harmony():
    spec = build_spec()
    spec.tracks = [t for t in spec.tracks if t.role not in ("melody", "harmony")]
    new_spec, report = optimize_arrangement(spec)
    roles = {t.role for t in new_spec.tracks}
    assert "melody" in roles
    assert "harmony" in roles
    assert any("melody" in c for c in report["changes"])
    validate_music_spec(new_spec)


def test_optimized_spec_valid_and_conservative():
    spec = build_spec()
    new_spec, report = optimize_arrangement(spec)
    validate_music_spec(new_spec)
    # 正常作品不应被大改
    assert len(new_spec.tracks) >= len(spec.tracks)
    assert new_spec.title == spec.title
