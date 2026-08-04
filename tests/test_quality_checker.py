"""质量检查与自动优化测试。"""

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
