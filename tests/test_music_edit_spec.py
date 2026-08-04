"""MusicEditSpec 协议测试。"""

from services.api.schemas.music_edit_spec import EditOperation, EditTarget, MusicEditSpec


def test_valid_edit_spec():
    spec = MusicEditSpec(
        instruction="副歌更亮一点",
        target=EditTarget(section="chorus", scope="section"),
        preserve=["version", "seed"],
        operations=[EditOperation(type="tonality", value="C")],
    )
    assert spec.version == "0.1"
    assert spec.target.scope == "section"


def test_mock_provider_generates_edit_spec():
    from packages.llm.mock_provider import MockProvider
    from services.api.schemas.music_spec import MusicSpec

    current = MusicSpec.model_validate(
        {
            "title": "t",
            "seed": 1,
            "prompt": "p",
            "tempo": {"bpm": 100, "feel": "medium"},
            "meter": {"numerator": 4, "denominator": 4},
            "tonality": {"key": "C", "mode": "major", "scale": None},
            "length": {"bars": 32},
            "style": ["pop"],
            "mood": ["bright"],
            "form": [{"id": "verse", "name": "主歌", "start_bar": 1, "bars": 8, "energy": 0.5}],
            "harmony": [{"section": "verse", "progression": ["C", "G", "Am", "F"]}],
            "tracks": [{"id": "bass", "role": "bass", "instrument": "bass", "velocity": 90}],
        }
    )
    edit = MockProvider().generate_music_edit("贝斯音量加大一点", current)
    assert edit.instruction == "贝斯音量加大一点"
    assert edit.target.scope == "track"
    assert edit.target.track == "bass"
    assert any(op.type == "velocity" for op in edit.operations)
