"""T22：PadEngine 长音 / 段落层次测试。"""

from packages.music_core.arrangement.pad_engine import PadEngine
from packages.music_core.bass.bass_engine import BassEngine
from packages.music_core.harmony.harmony_engine import build_bar_harmony
from services.api.schemas.music_spec import MusicSpec


def _spec() -> MusicSpec:
    return MusicSpec.model_validate(
        {
            "version": "0.1",
            "title": "Pad 测试",
            "seed": 23,
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
                {"id": "pad", "role": "pad", "instrument": "pad_2_warm", "velocity": 70},
                {"id": "bass", "role": "bass", "instrument": "electric_bass_finger", "velocity": 90},
            ],
            "notes": None,
        }
    )


def _by_section():
    spec = _spec()
    harmony = build_bar_harmony(spec)
    pad_track = next(t for t in spec.tracks if t.role == "pad")
    notes = PadEngine().generate(spec, harmony, pad_track, channel=3)
    sections: dict[str, list] = {}
    for note in notes:
        bar = int(note.start_beat // 4) + 1
        for section in spec.form:
            if section.start_bar <= bar < section.start_bar + section.bars:
                sections.setdefault(section.id, []).append(note)
                break
    return spec, notes, sections


def test_pad_not_empty_and_long():
    _, notes, _ = _by_section()
    assert notes
    long_ratio = sum(1 for n in notes if n.duration_beats >= 3.0) / len(notes)
    assert long_ratio >= 0.5


def test_pad_register_valid():
    _, notes, _ = _by_section()
    assert all(48 <= n.pitch <= 84 for n in notes)
    assert all(n.duration_beats > 0 for n in notes)
    assert all(1 <= n.velocity <= 127 for n in notes)


def test_chorus_not_thinner_than_verse():
    _, _, sections = _by_section()
    assert len(sections["chorus"]) >= len(sections["verse"])
    avg_vel = lambda ns: sum(n.velocity for n in ns) / len(ns)
    assert avg_vel(sections["chorus"]) >= avg_vel(sections["verse"]) - 2


def test_bridge_differs_from_chorus():
    _, _, sections = _by_section()
    bridge_pcs = {(n.pitch % 12, round(n.start_beat % 4, 2)) for n in sections["bridge"]}
    chorus_pcs = {(n.pitch % 12, round(n.start_beat % 4, 2)) for n in sections["chorus"]}
    assert bridge_pcs != chorus_pcs


def test_outro_thinning():
    _, _, sections = _by_section()
    assert len(sections["outro"]) < len(sections["chorus"])


def test_pad_above_bass():
    spec, notes, _ = _by_section()
    harmony = build_bar_harmony(spec)
    bass = BassEngine().generate(spec, harmony, channel=2)
    pad_avg = sum(n.pitch for n in notes) / len(notes)
    bass_avg = sum(n.pitch for n in bass) / len(bass)
    assert pad_avg >= bass_avg + 8
