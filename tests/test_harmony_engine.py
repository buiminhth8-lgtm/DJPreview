"""和声引擎测试。"""

from services.api.schemas.music_spec import MusicSpec
from packages.music_core.harmony.harmony_engine import build_bar_harmony


def build_spec(seed: int = 1) -> MusicSpec:
    return MusicSpec.model_validate(
        {
            "version": "0.1",
            "title": "和声测试",
            "seed": seed,
            "language": "zh-CN",
            "prompt": "测试",
            "tempo": {"bpm": 72, "feel": "slow"},
            "meter": {"numerator": 4, "denominator": 4},
            "tonality": {"key": "D", "mode": "minor", "scale": None},
            "length": {"bars": 32},
            "style": ["cinematic"],
            "mood": ["忧郁"],
            "form": [
                {"id": "intro", "name": "前奏", "start_bar": 1, "bars": 4, "energy": 0.2},
                {"id": "verse", "name": "主歌", "start_bar": 5, "bars": 8, "energy": 0.5},
                {"id": "chorus", "name": "副歌", "start_bar": 13, "bars": 16, "energy": 0.9},
                {"id": "outro", "name": "尾奏", "start_bar": 29, "bars": 4, "energy": 0.3},
            ],
            "harmony": [
                {"section": "intro", "progression": ["Dm"]},
                {"section": "verse", "progression": ["Dm", "Bb", "F", "C"]},
                {"section": "chorus", "progression": ["Dm", "Bb", "F", "C", "Bb", "C"]},
                {"section": "outro", "progression": ["Dm"]},
            ],
            "tracks": [
                {"id": "melody", "role": "melody", "instrument": "lead_synth", "velocity": 100},
                {"id": "piano", "role": "harmony", "instrument": "piano", "velocity": 80},
                {"id": "bass", "role": "bass", "instrument": "bass", "velocity": 90},
                {"id": "drums", "role": "drums", "instrument": "drums", "velocity": 100},
                {"id": "pad", "role": "pad", "instrument": "strings", "velocity": 70},
            ],
            "notes": None,
        }
    )


def test_build_bar_harmony_32_bars():
    spec = build_spec()
    harmony = build_bar_harmony(spec)
    assert len(harmony) == 32


def test_every_bar_has_chord():
    harmony = build_bar_harmony(build_spec())
    assert all(bar.chord_symbol for bar in harmony)


def test_every_bar_has_pitches():
    harmony = build_bar_harmony(build_spec())
    assert all(len(bar.chord_pitches) >= 3 for bar in harmony)


def test_bar_order_and_sections():
    harmony = build_bar_harmony(build_spec())
    assert [bar.bar_index for bar in harmony] == list(range(1, 33))
    assert harmony[0].section_id == "intro"
    assert harmony[12].section_id == "chorus"
    assert harmony[28].section_id == "outro"
