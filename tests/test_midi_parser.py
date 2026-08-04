"""MIDI Parser 测试。"""

import mido

from packages.music_core.analysis.midi_parser import parse_midi_to_notes
from packages.music_core.composer.music_composer import compose_music
from packages.music_core.midi.midi_writer import write_midi
from tests.test_harmony_engine import build_spec


def test_parse_composed_midi(tmp_path):
    midi_path = write_midi(compose_music(build_spec()), tmp_path / "output.mid")
    parsed = parse_midi_to_notes(midi_path)
    assert parsed.ticks_per_beat == 480
    assert parsed.tracks
    all_notes = [n for t in parsed.tracks for n in t.notes]
    assert all_notes
    assert all(n.start_beat >= 0 for n in all_notes)
    assert all(n.duration_beats > 0 for n in all_notes)


def test_note_on_velocity_zero_is_note_off(tmp_path):
    midi = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    track.append(mido.Message("note_on", note=60, velocity=100, time=0, channel=0))
    track.append(mido.Message("note_on", note=60, velocity=0, time=480, channel=0))
    track.append(mido.MetaMessage("end_of_track"))
    midi.tracks.append(track)
    path = tmp_path / "vel0.mid"
    midi.save(str(path))

    parsed = parse_midi_to_notes(path)
    notes = [n for t in parsed.tracks for n in t.notes]
    assert len(notes) == 1
    assert notes[0].duration_beats == 1.0


def test_drum_channel_marked(tmp_path):
    midi = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    track.append(mido.Message("note_on", note=36, velocity=100, time=0, channel=9))
    track.append(mido.Message("note_off", note=36, velocity=0, time=240, channel=9))
    track.append(mido.MetaMessage("end_of_track"))
    midi.tracks.append(track)
    path = tmp_path / "drums.mid"
    midi.save(str(path))

    parsed = parse_midi_to_notes(path)
    notes = [n for t in parsed.tracks for n in t.notes]
    assert len(notes) == 1
    assert notes[0].is_drum is True
    assert notes[0].pitch_name == "C2"


def _all_notes(parsed):
    return [n for t in parsed.tracks for n in t.notes]


def test_overlapping_same_note_parsed_as_two(tmp_path):
    """T16：同轨道同音高重叠 note_on/note_off 不丢失，FIFO 配对。"""
    midi = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    track.append(mido.Message("note_on", note=60, velocity=80, time=0, channel=0))
    track.append(mido.Message("note_on", note=60, velocity=90, time=120, channel=0))
    track.append(mido.Message("note_off", note=60, velocity=0, time=120, channel=0))
    track.append(mido.Message("note_off", note=60, velocity=0, time=120, channel=0))
    track.append(mido.MetaMessage("end_of_track"))
    midi.tracks.append(track)
    path = tmp_path / "overlap.mid"
    midi.save(str(path))

    parsed = parse_midi_to_notes(path)
    notes = _all_notes(parsed)
    assert len(notes) == 2
    assert notes[0].pitch == 60
    assert notes[1].pitch == 60
    assert notes[0].start_beat == 0.0
    assert notes[1].start_beat == round(120 / 480, 4)
    assert notes[0].duration_beats == round(240 / 480, 4)
    assert notes[1].duration_beats == round(240 / 480, 4)
    assert notes[0].velocity == 80
    assert notes[1].velocity == 90
    assert all(n.duration_beats > 0 for n in notes)


def test_multi_channel_same_note_not_confused(tmp_path):
    """T16：不同 channel 的同音高不互相配对。"""
    midi = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    track.append(mido.Message("note_on", note=60, velocity=80, time=0, channel=0))
    track.append(mido.Message("note_on", note=60, velocity=90, time=0, channel=1))
    track.append(mido.Message("note_off", note=60, velocity=0, time=240, channel=0))
    track.append(mido.Message("note_off", note=60, velocity=0, time=240, channel=1))
    track.append(mido.MetaMessage("end_of_track"))
    midi.tracks.append(track)
    path = tmp_path / "multi_ch.mid"
    midi.save(str(path))

    parsed = parse_midi_to_notes(path)
    notes = _all_notes(parsed)
    assert len(notes) == 2
    assert sorted(n.channel for n in notes) == [0, 1]
    assert {n.velocity for n in notes} == {80, 90}
    by_channel = {n.channel: n.duration_beats for n in notes}
    assert by_channel[0] == 0.5  # tick 240
    assert by_channel[1] == 1.0  # tick 480


def test_unpaired_note_off_does_not_crash(tmp_path):
    """T16：未配对 note_off 忽略，不崩溃。"""
    midi = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    track.append(mido.Message("note_off", note=60, velocity=0, time=0, channel=0))
    track.append(mido.MetaMessage("end_of_track"))
    midi.tracks.append(track)
    path = tmp_path / "unpaired.mid"
    midi.save(str(path))

    parsed = parse_midi_to_notes(path)
    assert _all_notes(parsed) == []


def test_unclosed_note_on_at_eof_does_not_crash(tmp_path):
    """T16：文件结束仍有未关闭 note_on 不崩溃（按项目现有行为丢弃）。"""
    midi = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    track.append(mido.Message("note_on", note=60, velocity=80, time=0, channel=0))
    track.append(mido.MetaMessage("end_of_track"))
    midi.tracks.append(track)
    path = tmp_path / "unclosed.mid"
    midi.save(str(path))

    parsed = parse_midi_to_notes(path)
    assert _all_notes(parsed) == []
