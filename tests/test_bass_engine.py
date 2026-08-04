"""T21：BassEngine 段落强度 / approach / kick 对齐 / 调内性测试。"""

from packages.music_core.analysis.bass_analysis import bass_kick_alignment_score
from packages.music_core.bass.bass_engine import BassEngine, extract_kick_positions
from packages.music_core.drums.drum_engine import DrumEngine
from packages.music_core.harmony.harmony_engine import build_bar_harmony
from packages.music_core.theory.scales import get_scale_pitches
from services.api.schemas.music_spec import MusicSpec


def _spec() -> MusicSpec:
    return MusicSpec.model_validate(
        {
            "version": "0.1",
            "title": "贝斯测试",
            "seed": 9,
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
                {"id": "bass", "role": "bass", "instrument": "electric_bass_finger", "velocity": 90},
            ],
            "notes": None,
        }
    )


def _bass_by_section(kick_positions=None):
    spec = _spec()
    harmony = build_bar_harmony(spec)
    notes = BassEngine().generate(spec, harmony, channel=2, kick_positions=kick_positions)
    sections: dict[str, list] = {}
    for note in notes:
        bar = int(note.start_beat // 4) + 1
        for section in spec.form:
            if section.start_bar <= bar < section.start_bar + section.bars:
                sections.setdefault(section.id, []).append(note)
                break
    return spec, sections


def test_verse_and_chorus_have_bass():
    _, sections = _bass_by_section()
    assert sections.get("verse")
    assert sections.get("chorus")


def test_chorus_stronger_than_verse():
    _, sections = _bass_by_section()
    verse = sections["verse"]
    chorus = sections["chorus"]
    assert len(chorus) >= len(verse)
    avg_vel = lambda ns: sum(n.velocity for n in ns) / len(ns)
    assert avg_vel(chorus) >= avg_vel(verse) - 2
    span = lambda ns: max(n.pitch for n in ns) - min(n.pitch for n in ns)
    assert span(chorus) >= span(verse)


def test_strong_beat_follows_chord_root():
    spec, sections = _bass_by_section()
    verse = sections["verse"]
    # verse 从第 3 小节开始（start_beat=8）；第一小节和弦为 C
    first_bar = [n for n in verse if 8.0 <= n.start_beat < 12.0 and n.start_beat % 4.0 < 0.1]
    assert first_bar
    root_pc = 0  # C major tonic
    assert any(n.pitch % 12 == root_pc for n in first_bar)


def test_pre_chorus_ends_with_approach():
    _, sections = _bass_by_section()
    pre = sections["pre_chorus"]
    # pre_chorus 末小节最后 0.5 拍存在 approach 音
    tail = [n for n in pre if 31.5 <= n.start_beat < 32.0]
    assert tail


def test_bridge_differs_from_chorus():
    _, sections = _bass_by_section()
    bridge = sections["bridge"]
    chorus = sections["chorus"]
    bridge_pattern = {(n.pitch, round(n.start_beat % 4, 2)) for n in bridge}
    chorus_pattern = {(n.pitch, round(n.start_beat % 4, 2)) for n in chorus}
    assert bridge_pattern != chorus_pattern


def test_outro_ends_on_tonic():
    _, sections = _bass_by_section()
    outro = sections["outro"]
    last = max(outro, key=lambda n: n.start_beat)
    assert last.pitch % 12 == 0  # C major tonic


def test_kick_alignment():
    spec = _spec()
    harmony = build_bar_harmony(spec)
    drums = DrumEngine().generate(spec, harmony, channel=9)
    kicks = extract_kick_positions(drums)
    assert kicks
    bass = BassEngine().generate(spec, harmony, channel=2, kick_positions=kicks)
    ratio = bass_kick_alignment_score(bass, kicks, tolerance=0.3)
    assert ratio >= 0.5


def test_without_drum_events_does_not_crash():
    _, sections = _bass_by_section(kick_positions=None)
    assert sections.get("verse")


def test_bass_in_scale_and_range():
    spec, sections = _bass_by_section()
    notes = [n for section in sections.values() for n in section]
    scale = get_scale_pitches("C", "major", 4)
    scale_mods = {p % 12 for p in scale}
    in_scale = sum(1 for n in notes if n.pitch % 12 in scale_mods)
    assert in_scale / len(notes) >= 0.85
    assert all(24 <= n.pitch <= 64 for n in notes)
    assert all(n.duration_beats > 0 for n in notes)
    assert all(1 <= n.velocity <= 127 for n in notes)
