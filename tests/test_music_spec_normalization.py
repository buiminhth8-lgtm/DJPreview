"""T36：MusicSpec 乐器名归一化测试（LLM 输出 → canonical）。"""

from packages.music_core.normalization.instrument_normalizer import normalize_music_spec
from packages.music_core.validation.spec_validator import validate_music_spec_semantics
from services.api.schemas.music_spec import TrackSpec
from tests.test_harmony_engine import build_spec


def _spec_with_gemini_tracks():
    """模拟 Gemini 返回的 brass / distorted guitar 轨道。"""
    spec = build_spec()
    base = [t for t in spec.tracks if t.role not in ("melody", "harmony")]
    spec.tracks = [
        *base,
        TrackSpec(
            id="brass_epic",
            role="melody",
            instrument="brass",
            pattern="sustained",
            register="mid-high",
            velocity=110,
        ),
        TrackSpec(
            id="dist_guitar",
            role="harmony",
            instrument="electric_guitar_distorted",
            pattern="power_chords",
            register="mid",
            velocity=105,
        ),
    ]
    return spec


def test_normalize_brass_track():
    spec = _spec_with_gemini_tracks()
    spec, records = normalize_music_spec(spec)
    brass = next(t for t in spec.tracks if t.id == "brass_epic")
    assert brass.instrument == "brass_section"
    # 保留其它字段
    assert brass.role == "melody"
    assert brass.pattern == "sustained"
    assert brass.register == "mid-high"
    assert brass.velocity == 110
    changed = [r for r in records if r.track_id == "brass_epic"]
    assert changed and changed[0].changed is True
    assert changed[0].original == "brass"
    assert changed[0].normalized == "brass_section"


def test_normalize_dist_guitar_track():
    spec = _spec_with_gemini_tracks()
    spec, records = normalize_music_spec(spec)
    guitar = next(t for t in spec.tracks if t.id == "dist_guitar")
    assert guitar.instrument == "distortion_guitar"
    assert guitar.role == "harmony"
    assert guitar.pattern == "power_chords"
    assert guitar.register == "mid"
    assert guitar.velocity == 105


def test_normalize_preserves_track_id_and_other_tracks():
    spec = _spec_with_gemini_tracks()
    original_ids = [t.id for t in spec.tracks]
    spec, _ = normalize_music_spec(spec)
    assert [t.id for t in spec.tracks] == original_ids


def test_normalized_spec_no_unknown_instrument_warnings():
    spec = _spec_with_gemini_tracks()
    spec, _ = normalize_music_spec(spec)
    result = validate_music_spec_semantics(spec)
    codes = {w.code for w in result.warnings}
    assert "UNKNOWN_INSTRUMENT_ALIAS" not in codes


def test_validation_does_not_warn_on_raw_aliases():
    """即使不先 normalize，validator 也应基于 canonical 判断 brass / distorted guitar。"""
    spec = _spec_with_gemini_tracks()
    result = validate_music_spec_semantics(spec)
    codes = {w.code for w in result.warnings}
    assert "UNKNOWN_INSTRUMENT_ALIAS" not in codes
    brass = next(t for t in spec.tracks if t.id == "brass_epic")
    assert brass.instrument == "brass_section"
