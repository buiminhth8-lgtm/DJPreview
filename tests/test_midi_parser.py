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
