"""T20：DrumEngine 段落强度 / fill / crash / 对比测试。"""

from packages.music_core.drums.drum_engine import DrumEngine
from packages.music_core.harmony.harmony_engine import build_bar_harmony
from services.api.schemas.music_spec import MusicSpec


def _spec() -> MusicSpec:
    return MusicSpec.model_validate(
        {
            "version": "0.1",
            "title": "鼓组测试",
            "seed": 7,
            "language": "zh-CN",
            "prompt": "test",
            "tempo": {"bpm": 96, "feel": "medium"},
            "meter": {"numerator": 4, "denominator": 4},
            "tonality": {"key": "C", "mode": "major", "scale": None},
            "length": {"bars": 20},
            "style": ["pop"],
            "mood": ["bright"],
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
                {"id": "drums", "role": "drums", "instrument": "standard_drum_kit", "velocity": 100},
            ],
            "notes": None,
        }
    )


def _by_section():
    spec = _spec()
    notes = DrumEngine().generate(spec, build_bar_harmony(spec), channel=9)
    sections: dict[str, list] = {}
    for note in notes:
        bar = int(note.start_beat // 4) + 1
        for section in spec.form:
            if section.start_bar <= bar < section.start_bar + section.bars:
                sections.setdefault(section.id, []).append(note)
                break
    return notes, sections


def test_verse_and_chorus_have_drums():
    notes, sections = _by_section()
    assert notes
    assert sections.get("verse")
    assert sections.get("chorus")


def test_chorus_stronger_than_verse():
    _, sections = _by_section()
    verse = sections["verse"]
    chorus = sections["chorus"]
    assert len(chorus) >= len(verse)
    avg_vel = lambda ns: sum(n.velocity for n in ns) / len(ns)
    assert avg_vel(chorus) >= avg_vel(verse) - 2


def test_pre_chorus_end_has_fill():
    _, sections = _by_section()
    pre = sections["pre_chorus"]
    # pre_chorus 第 2 小节（末小节）最后 1 拍存在 >=2 个 fill 击打
    end = 8 * 4  # bar 8 start = (8-1)*4 = 28；末小节 28..32
    tail = [n for n in pre if 31.0 <= n.start_beat < 32.0]
    assert len(tail) >= 2


def test_chorus_first_beat_crash():
    _, sections = _by_section()
    chorus = sections["chorus"]
    first_bar_start = 8 * 4  # bar 9 start = 32
    crash = [n for n in chorus if n.pitch == 49 and abs(n.start_beat - first_bar_start) < 0.05]
    assert crash


def test_bridge_differs_from_chorus():
    _, sections = _by_section()
    bridge = sections["bridge"]
    chorus = sections["chorus"]
    bridge_pattern = {(n.pitch, round(n.start_beat % 4, 2)) for n in bridge}
    chorus_pattern = {(n.pitch, round(n.start_beat % 4, 2)) for n in chorus}
    assert bridge_pattern != chorus_pattern


def test_outro_has_notes_and_no_crash():
    _, sections = _by_section()
    outro = sections["outro"]
    assert outro
    assert all(n.pitch != 49 for n in outro)  # outro 不放置 crash


def test_all_drum_events_valid():
    notes, _ = _by_section()
    assert all(1 <= n.velocity <= 127 for n in notes)
    assert all(0 <= n.pitch <= 127 for n in notes)
    assert all(n.start_beat >= 0 and n.duration_beats > 0 for n in notes)
    assert all(n.channel == 9 and n.is_drum for n in notes)
