"""T22：StringsEngine 段落层次测试。"""

from packages.music_core.arrangement.strings_engine import StringsEngine
from packages.music_core.harmony.harmony_engine import build_bar_harmony
from services.api.schemas.music_spec import MusicSpec


def _spec() -> MusicSpec:
    return MusicSpec.model_validate(
        {
            "version": "0.1",
            "title": "弦乐测试",
            "seed": 21,
            "language": "zh-CN",
            "prompt": "test",
            "tempo": {"bpm": 96, "feel": "medium"},
            "meter": {"numerator": 4, "denominator": 4},
            "tonality": {"key": "C", "mode": "major", "scale": None},
            "length": {"bars": 20},
            "style": ["cinematic"],
            "mood": ["epic"],
            "form": [
                {"id": "intro", "name": "前奏", "start_bar": 1, "bars": 2, "energy": 0.2},
                {"id": "verse", "name": "主歌", "start_bar": 3, "bars": 4, "energy": 0.5},
                {"id": "pre_chorus", "name": "前副歌", "start_bar": 7, "bars": 2, "energy": 0.7},
                {"id": "chorus", "name": "副歌", "start_bar": 9, "bars": 8, "energy": 0.9},
                {"id": "bridge", "name": "桥段", "start_bar": 17, "bars": 2, "energy": 0.5},
                {"id": "outro", "name": "尾奏", "start_bar": 19, "bars": 2, "energy": 0.3},
            ],
            "harmony": [
                {"section": "intro", "progression": ["C"]},
                {"section": "verse", "progression": ["C", "G", "Am", "F"]},
                {"section": "pre_chorus", "progression": ["F", "G"]},
                {"section": "chorus", "progression": ["C", "G", "Am", "F"]},
                {"section": "bridge", "progression": ["Am", "F"]},
                {"section": "outro", "progression": ["C"]},
            ],
            "tracks": [
                {"id": "strings", "role": "strings", "instrument": "string_ensemble_1", "velocity": 70},
            ],
            "notes": None,
        }
    )


def _by_section():
    spec = _spec()
    harmony = build_bar_harmony(spec)
    track = spec.tracks[0]
    notes = StringsEngine().generate(spec, harmony, track, channel=3)
    sections: dict[str, list] = {}
    for note in notes:
        bar = int(note.start_beat // 4) + 1
        for section in spec.form:
            if section.start_bar <= bar < section.start_bar + section.bars:
                sections.setdefault(section.id, []).append(note)
                break
    return notes, sections


def test_strings_not_empty():
    notes, _ = _by_section()
    assert notes


def test_chorus_stronger_than_verse():
    _, sections = _by_section()
    verse = sections["verse"]
    chorus = sections["chorus"]
    assert len(chorus) >= len(verse)
    avg_vel = lambda ns: sum(n.velocity for n in ns) / len(ns)
    assert avg_vel(chorus) >= avg_vel(verse) - 2


def test_pre_chorus_build():
    _, sections = _by_section()
    pre = sections["pre_chorus"]
    verse = sections["verse"]
    assert pre
    avg_vel = lambda ns: sum(n.velocity for n in ns) / len(ns)
    assert avg_vel(pre) >= avg_vel(verse)


def test_outro_thinning():
    _, sections = _by_section()
    outro = sections["outro"]
    chorus = sections["chorus"]
    assert outro
    assert len(outro) < len(chorus)
    avg_vel = lambda ns: sum(n.velocity for n in ns) / len(ns)
    assert avg_vel(outro) <= avg_vel(chorus)


def test_strings_register_and_duration():
    notes, _ = _by_section()
    assert all(48 <= n.pitch <= 88 for n in notes)
    assert all(n.duration_beats > 0 for n in notes)
    assert all(1 <= n.velocity <= 127 for n in notes)
