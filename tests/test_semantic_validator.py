"""T10 MusicSpec 语义校验（ValidationResult / validate_music_spec_semantics）测试。"""

from fastapi.testclient import TestClient

from packages.llm.factory import get_llm_provider
from packages.music_core.validation.spec_validator import (
    ValidationResult,
    validate_music_spec_semantics,
)
from services.api.main import app
from services.api.schemas.music_spec import HarmonySectionSpec
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


def test_drums_low_tom_percussion_no_unknown_warning():
    spec = build_spec()
    spec.tracks = [
        *[t for t in spec.tracks if t.role != "drums"],
        type(spec.tracks[0])(
            id="toms",
            role="drums",
            instrument="low_tom_percussion",
            pattern="cinematic_toms",
            register=None,
            velocity=90,
        ),
    ]
    result = validate_music_spec_semantics(spec)
    assert "UNKNOWN_INSTRUMENT_ALIAS" not in _codes(result, "warnings")
    drums = next(t for t in spec.tracks if t.role == "drums")
    assert drums.instrument == "standard_drum_kit"
    assert drums.pattern == "cinematic_toms"


def _cadence_warnings(harmony):
    spec = build_spec()
    spec.harmony = [HarmonySectionSpec(**h) for h in harmony]
    return _codes(validate_music_spec_semantics(spec), "warnings")


def _cadence_warnings_c_major(harmony):
    spec = build_spec()
    spec.tonality = type(spec.tonality)(key="C", mode="major", scale=None)
    spec.harmony = [HarmonySectionSpec(**h) for h in harmony]
    return _codes(validate_music_spec_semantics(spec), "warnings")


def test_authentic_cadence_no_warning():
    # C major：G7 → C
    assert "WEAK_SECTION_CADENCE" not in _cadence_warnings_c_major(
        [
            {"section": "intro", "progression": ["C"]},
            {"section": "verse", "progression": ["C", "G", "Am", "F"]},
            {"section": "chorus", "progression": ["C", "G", "G7", "C"]},
            {"section": "outro", "progression": ["F", "C"]},
        ]
    )
    # D minor：A7 → Dm
    assert "WEAK_SECTION_CADENCE" not in _cadence_warnings(
        [
            {"section": "intro", "progression": ["Dm"]},
            {"section": "verse", "progression": ["Dm", "Bb", "F", "C"]},
            {"section": "chorus", "progression": ["Dm", "Bb", "A7", "Dm"]},
            {"section": "outro", "progression": ["A7", "Dm"]},
        ]
    )


def test_plagal_cadence_no_warning():
    # C major：F → C
    assert "WEAK_SECTION_CADENCE" not in _cadence_warnings_c_major(
        [
            {"section": "intro", "progression": ["C"]},
            {"section": "verse", "progression": ["C", "G", "Am", "F"]},
            {"section": "chorus", "progression": ["C", "G", "Am", "F", "C"]},
            {"section": "outro", "progression": ["F", "C"]},
        ]
    )


def test_minor_authentic_cadence_no_warning():
    spec = build_spec()
    spec.tonality = type(spec.tonality)(key="A", mode="minor", scale=None)
    spec.harmony = [
        HarmonySectionSpec(**{"section": "intro", "progression": ["Am"]}),
        HarmonySectionSpec(**{"section": "verse", "progression": ["Am", "F", "G", "E7"]}),
        HarmonySectionSpec(**{"section": "chorus", "progression": ["Am", "F", "E7", "Am"]}),
        HarmonySectionSpec(**{"section": "outro", "progression": ["E7", "Am"]}),
    ]
    result = validate_music_spec_semantics(spec)
    assert "WEAK_SECTION_CADENCE" not in _codes(result, "warnings")


def test_weak_cadence_still_warns():
    warnings = _cadence_warnings_c_major(
        [
            {"section": "intro", "progression": ["C"]},
            {"section": "verse", "progression": ["C", "G", "Am", "F"]},
            {"section": "chorus", "progression": ["C", "G", "Am", "F"]},
            {"section": "outro", "progression": ["Am", "F"]},
        ]
    )
    # 末和弦非主和弦（F）：weak cadence 仍告警
    assert "WEAK_SECTION_CADENCE" in warnings


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


# ---------- T19：和声扩展与终止式 warnings ----------

def test_extended_chords_pass_validation():
    spec = build_spec()
    spec.harmony[2] = spec.harmony[2].model_copy(
        update={"progression": ["Cmaj7", "Am7", "Dm7", "G7", "Csus4", "Cadd9"]}
    )
    result = validate_music_spec_semantics(spec)
    assert result.valid
    assert "INVALID_CHORD_SYMBOL" not in _codes(result)


def test_weak_section_cadence_is_warning():
    spec = build_spec()
    # chorus 结尾非终止式（末和弦不是主和弦）
    spec.harmony[2] = spec.harmony[2].model_copy(update={"progression": ["Dm", "Bb", "F", "C"]})
    result = validate_music_spec_semantics(spec)
    assert result.valid
    assert "WEAK_SECTION_CADENCE" in _codes(result, "warnings")


def test_repetitive_progression_is_warning():
    spec = build_spec()
    spec.harmony[1] = spec.harmony[1].model_copy(
        update={"progression": ["Dm", "Dm", "Dm", "Dm"]}
    )
    result = validate_music_spec_semantics(spec)
    assert result.valid
    assert "REPETITIVE_CHORD_PROGRESSION" in _codes(result, "warnings")
