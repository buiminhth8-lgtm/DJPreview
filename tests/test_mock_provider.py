"""MockProvider 规则测试。"""

from packages.music_core.instruments.registry import is_known_instrument
from packages.llm.mock_provider import MockProvider
from packages.music_core.validation.spec_validator import validate_music_spec
from packages.music_core.validation.spec_validator import validate_music_spec_semantics


def test_sad_prompt_returns_minor():
    spec = MockProvider().generate_music_spec("生成一段忧郁悲伤的雨夜钢琴曲")
    assert spec.tonality.mode == "minor"
    assert spec.tonality.key == "D"
    assert spec.tempo.bpm == 72


def test_happy_prompt_returns_major():
    spec = MockProvider().generate_music_spec("一首欢快明亮的流行歌")
    assert spec.tonality.mode == "major"
    assert spec.tonality.key == "C"
    assert spec.tempo.bpm == 120


def test_chinese_style_returns_pentatonic():
    spec = MockProvider().generate_music_spec("带有中国风韵味的旋律")
    assert spec.tonality.mode == "pentatonic"


def test_mock_spec_always_valid():
    spec = MockProvider().generate_music_spec("生成一段忧郁空灵的钢琴配乐")
    validated = validate_music_spec(spec)
    assert validated.length.bars == 32
    assert len(validated.tracks) >= 5


def test_all_mock_instruments_resolvable():
    """T17：MockProvider 输出 canonical 乐器，均能被 registry 识别。"""
    prompts = (
        "生成一段忧郁空灵的钢琴配乐",
        "带有中国风韵味的旋律",
        "chill 的 lo-fi hiphop 伴奏",
        "强劲有力的摇滚主题曲",
    )
    for prompt in prompts:
        spec = MockProvider().generate_music_spec(prompt)
        assert spec.tracks
        for track in spec.tracks:
            assert is_known_instrument(track.instrument), (track.id, track.instrument)


def test_mock_spec_semantic_validation_no_unknown_instrument():
    spec = MockProvider().generate_music_spec("生成一段忧郁空灵的钢琴配乐")
    result = validate_music_spec_semantics(spec)
    assert result.valid
    codes = {i.code for i in result.errors} | {i.code for i in result.warnings}
    assert "UNKNOWN_INSTRUMENT_ALIAS" not in codes
