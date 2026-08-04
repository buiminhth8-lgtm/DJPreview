"""T10 MusicSpec 语义校验（ValidationResult / validate_music_spec_semantics）测试。"""

from fastapi.testclient import TestClient

from packages.llm.factory import get_llm_provider
from packages.music_core.validation.spec_validator import (
    ValidationResult,
    validate_music_spec_semantics,
)
from services.api.main import app
from services.api.storage.project_store import create_project
from tests.test_harmony_engine import build_spec

client = TestClient(app)


def _mock_spec():
    """通过 MockProvider 生成合法 MusicSpec。"""
    return get_llm_provider("mock").generate_music_spec("生成一段忧郁空灵的钢琴配乐")


def _codes(result: ValidationResult, kind: str = "errors") -> set[str]:
    return {issue.code for issue in getattr(result, kind)}


def test_mock_provider_spec_is_valid():
    result = validate_music_spec_semantics(_mock_spec())
    assert result.valid
    assert result.errors == []


def test_duplicate_track_id():
    spec = build_spec()
    spec.tracks[1] = spec.tracks[1].model_copy(update={"id": "melody"})
    result = validate_music_spec_semantics(spec)
    assert not result.valid
    assert "DUPLICATE_TRACK_ID" in _codes(result)


def test_duplicate_section_id():
    spec = build_spec()
    spec.form[1] = spec.form[1].model_copy(update={"id": "intro"})
    result = validate_music_spec_semantics(spec)
    assert not result.valid
    assert "DUPLICATE_SECTION_ID" in _codes(result)


def test_section_overlap():
    spec = build_spec()
    spec.form[2] = spec.form[2].model_copy(update={"start_bar": 8, "bars": 8})
    result = validate_music_spec_semantics(spec)
    assert not result.valid
    assert "SECTION_OVERLAP" in _codes(result)


def test_section_out_of_range():
    spec = build_spec()
    spec.form[0] = spec.form[0].model_copy(update={"start_bar": 30, "bars": 4})
    result = validate_music_spec_semantics(spec)
    assert not result.valid
    assert "SECTION_OUT_OF_RANGE" in _codes(result)


def test_unknown_harmony_section():
    spec = build_spec()
    spec.harmony[0] = spec.harmony[0].model_copy(update={"section": "bridge"})
    result = validate_music_spec_semantics(spec)
    assert not result.valid
    assert "UNKNOWN_HARMONY_SECTION" in _codes(result)


def test_unknown_enabled_section():
    spec = build_spec()
    spec.tracks[0] = spec.tracks[0].model_copy(update={"enabled_sections": ["chorus", "nope"]})
    result = validate_music_spec_semantics(spec)
    assert not result.valid
    assert "UNKNOWN_ENABLED_SECTION" in _codes(result)


def test_invalid_key():
    spec = build_spec()
    spec.tonality = spec.tonality.model_copy(update={"key": "H"})
    result = validate_music_spec_semantics(spec)
    assert not result.valid
    assert "INVALID_KEY" in _codes(result)


def test_invalid_mode():
    spec = build_spec()
    spec.tonality = spec.tonality.model_copy(update={"mode": "mystery_mode"})
    result = validate_music_spec_semantics(spec)
    assert not result.valid
    assert "INVALID_MODE" in _codes(result)


def test_invalid_meter_denominator():
    spec = build_spec()
    spec.meter = spec.meter.model_copy(update={"denominator": 3})
    result = validate_music_spec_semantics(spec)
    assert not result.valid
    assert "INVALID_METER_DENOMINATOR" in _codes(result)


def test_invalid_chord_symbol():
    spec = build_spec()
    spec.harmony[0] = spec.harmony[0].model_copy(update={"progression": ["H??"]})
    result = validate_music_spec_semantics(spec)
    assert not result.valid
    assert "INVALID_CHORD_SYMBOL" in _codes(result)


def test_section_coverage_gap_is_warning():
    spec = build_spec()
    # 去掉 outro（29-32 小节）后留下未被段落覆盖的小节，只应产生 warning
    spec.form = spec.form[:-1]
    spec.harmony = spec.harmony[:-1]
    result = validate_music_spec_semantics(spec)
    assert result.valid
    assert "SECTION_COVERAGE_GAP" in _codes(result, "warnings")


def test_midi_generate_rejects_invalid_spec():
    """非法 MusicSpec 的项目在 MIDI 生成时应被 400 阻断并返回统一错误码。"""
    spec = build_spec()
    spec.harmony[0] = spec.harmony[0].model_copy(update={"section": "ghost"})
    song_id = create_project(spec)
    resp = client.post(f"/api/v1/songs/{song_id}/midi/generate")
    assert resp.status_code == 400
    body = resp.json()
    assert body["error_code"] == "MUSIC_SPEC_VALIDATION_FAILED"
    assert any(item["code"] == "UNKNOWN_HARMONY_SECTION" for item in body["details"]["errors"])


# ---------- T17：未知乐器 warning ----------

def test_unknown_instrument_is_warning_not_error():
    spec = build_spec()
    spec.tracks[0] = spec.tracks[0].model_copy(update={"instrument": "theremin_xyz"})
    result = validate_music_spec_semantics(spec)
    assert result.valid
    assert "UNKNOWN_INSTRUMENT_ALIAS" in _codes(result, "warnings")


def test_known_alias_instrument_no_warning():
    spec = build_spec()
    spec.tracks[0] = spec.tracks[0].model_copy(update={"instrument": "piano"})
    result = validate_music_spec_semantics(spec)
    assert "UNKNOWN_INSTRUMENT_ALIAS" not in _codes(result, "warnings")


def test_canonical_instrument_no_warning():
    spec = build_spec()
    spec.tracks[1] = spec.tracks[1].model_copy(update={"instrument": "acoustic_grand_piano"})
    result = validate_music_spec_semantics(spec)
    assert "UNKNOWN_INSTRUMENT_ALIAS" not in _codes(result, "warnings")
