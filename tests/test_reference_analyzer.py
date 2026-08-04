"""参考 MIDI 分析测试。"""

import mido

from packages.llm.mock_provider import MockProvider
from packages.music_core.reference.reference_analyzer import analyze_reference_midi
from packages.music_core.reference.reference_to_spec import build_music_spec_from_reference
from packages.music_core.validation.spec_validator import validate_music_spec


def _make_reference_midi(tmp_path):
    midi = mido.MidiFile(ticks_per_beat=480)
    melody = mido.MidiTrack()
    melody.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(100)))
    melody.append(mido.Message("note_on", note=64, velocity=90, time=0, channel=0))
    melody.append(mido.Message("note_off", note=64, velocity=0, time=480, channel=0))
    melody.append(mido.Message("note_on", note=67, velocity=90, time=0, channel=0))
    melody.append(mido.Message("note_off", note=67, velocity=0, time=480, channel=0))
    melody.append(mido.MetaMessage("end_of_track"))
    drums = mido.MidiTrack()
    drums.append(mido.Message("note_on", note=36, velocity=100, time=0, channel=9))
    drums.append(mido.Message("note_off", note=36, velocity=0, time=240, channel=9))
    drums.append(mido.MetaMessage("end_of_track"))
    midi.tracks.append(melody)
    midi.tracks.append(drums)
    path = tmp_path / "reference.mid"
    midi.save(str(path))
    return path


def test_analyze_reference(tmp_path):
    path = _make_reference_midi(tmp_path)
    analysis = analyze_reference_midi(path)
    assert analysis.note_count > 0
    assert analysis.track_count > 0
    assert analysis.bpm == 100
    assert analysis.rhythm_profile["has_drums"] is True
    assert "drums" in analysis.possible_roles


def test_reference_to_spec_no_melody_copy(tmp_path):
    path = _make_reference_midi(tmp_path)
    analysis = analyze_reference_midi(path)
    spec = build_music_spec_from_reference("生成一段氛围配乐", analysis)
    validate_music_spec(spec)
    # 高层特征生效：bpm 接近参考
    assert abs(spec.tempo.bpm - analysis.bpm) <= 25
    # 不复制旋律：MusicSpec 没有参考的音符数据
    assert not any(getattr(t, "notes", None) for t in spec.tracks)


def test_reference_to_spec_with_base(tmp_path):
    path = _make_reference_midi(tmp_path)
    analysis = analyze_reference_midi(path)
    base = MockProvider().generate_music_spec("生成一段欢快的歌")
    spec = build_music_spec_from_reference("生成一段氛围配乐", analysis, base_spec=base)
    validate_music_spec(spec)
