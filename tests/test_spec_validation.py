"""MusicSpec 语义校验（errors / warnings 报告）测试。"""

import pytest

from packages.music_core.validation.spec_validator import (
    MusicSpecValidationError,
    ValidationReport,
    check_music_spec,
    validate_music_spec,
)
from tests.test_harmony_engine import build_spec


def _spec():
    return build_spec()


def _errors(report: ValidationReport) -> list[str]:
    return report.errors


def test_valid_spec_has_no_errors():
    report = check_music_spec(_spec())
    assert report.valid
    assert report.errors == []


def test_duplicate_track_id():
    spec = _spec()
    spec.tracks[0] = spec.tracks[0].model_copy(update={"id": "bass"})
    report = check_music_spec(spec)
    assert any("track_id 重复" in e for e in report.errors)


def test_duplicate_section_id():
    spec = _spec()
    spec.form[1] = spec.form[1].model_copy(update={"id": "intro"})
    report = check_music_spec(spec)
    assert any("section.id 重复" in e for e in report.errors)


def test_overlapping_sections():
    spec = _spec()
    spec.form[2] = spec.form[2].model_copy(update={"start_bar": 8, "bars": 8})  # 与 verse 重叠
    report = check_music_spec(spec)
    assert any("重叠" in e for e in report.errors)


def test_harmony_section_not_in_form():
    spec = _spec()
    spec.harmony[0] = spec.harmony[0].model_copy(update={"section": "bridge"})
    report = check_music_spec(spec)
    assert any("harmony.section" in e for e in report.errors)


def test_enabled_sections_missing():
    spec = _spec()
    spec.tracks[0] = spec.tracks[0].model_copy(update={"enabled_sections": ["chorus", "nope"]})
    report = check_music_spec(spec)
    assert any("enabled_sections" in e and "nope" in e for e in report.errors)


def test_invalid_key():
    spec = _spec()
    spec.tonality = spec.tonality.model_copy(update={"key": "H"})
    report = check_music_spec(spec)
    assert any("key" in e and "H" in e for e in report.errors)


def test_unknown_mode_is_warning():
    spec = _spec()
    spec.tonality = spec.tonality.model_copy(update={"mode": "mystery_mode"})
    report = check_music_spec(spec)
    assert report.valid
    assert any("未知调式" in w for w in report.warnings)


def test_unparseable_chord():
    spec = _spec()
    spec.harmony[0] = spec.harmony[0].model_copy(update={"progression": ["H??"]})
    report = check_music_spec(spec)
    assert any("无法解析" in e for e in report.errors)


def test_missing_harmony_config_is_warning():
    spec = _spec()
    spec.harmony = spec.harmony[:-1]  # 去掉 outro 的 harmony
    report = check_music_spec(spec)
    assert report.valid
    assert any("缺少 harmony 配置" in w for w in report.warnings)


def test_validate_raises_on_errors():
    spec = _spec()
    spec.tracks[0] = spec.tracks[0].model_copy(update={"id": "bass"})
    with pytest.raises(MusicSpecValidationError):
        validate_music_spec(spec)


def test_validate_accepts_dict_and_returns_spec():
    spec = validate_music_spec(_spec().model_dump(mode="json"))
    assert spec.title
