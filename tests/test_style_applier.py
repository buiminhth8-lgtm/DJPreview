"""StyleApplier 测试。"""

from packages.llm.mock_provider import MockProvider
from packages.music_core.styles.style_applier import apply_style_template_to_music_spec
from packages.music_core.styles.style_library import get_style_template
from packages.music_core.validation.spec_validator import validate_music_spec


def _base():
    return MockProvider().generate_music_spec("生成一段音乐")


def test_cinematic_piano_adds_strings_pad():
    template = get_style_template("cinematic_piano")
    spec = apply_style_template_to_music_spec(_base(), template, 0.8)
    roles = {t.role for t in spec.tracks}
    assert "melody" in roles
    assert "pad" in roles or "strings" in roles
    validate_music_spec(spec)


def test_chinese_cinematic_sets_pentatonic():
    template = get_style_template("chinese_cinematic")
    spec = apply_style_template_to_music_spec(_base(), template, 0.8)
    assert spec.tonality.mode == "pentatonic"
    validate_music_spec(spec)


def test_lo_fi_hiphop_includes_drums_bass():
    template = get_style_template("lo_fi_hiphop")
    spec = apply_style_template_to_music_spec(_base(), template, 0.8)
    roles = {t.role for t in spec.tracks}
    assert "drums" in roles
    assert "bass" in roles
    validate_music_spec(spec)


def test_strength_zero_minimal_change():
    template = get_style_template("game_battle")
    original = _base()
    spec = apply_style_template_to_music_spec(original, template, 0.0)
    assert spec.tempo.bpm == original.tempo.bpm


def test_strength_one_strong_influence():
    template = get_style_template("game_battle")
    spec = apply_style_template_to_music_spec(_base(), template, 1.0)
    assert "game" in spec.style or "battle" in spec.style
    assert spec.tempo.bpm >= 130
    validate_music_spec(spec)
