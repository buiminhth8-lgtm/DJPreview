"""MIDI Writer 测试。"""

import mido

from packages.music_core.composer.music_composer import compose_music
from packages.music_core.midi.midi_writer import write_midi
from tests.test_harmony_engine import build_spec


def test_write_midi_file(tmp_path):
    composition = compose_music(build_spec())
    output = tmp_path / "output.mid"
    written = write_midi(composition, output)
    assert written.exists()
    assert written.stat().st_size > 0

    midi = mido.MidiFile(str(written))
    assert len(midi.tracks) > 1
    assert midi.ticks_per_beat == 480


def test_midi_has_multiple_tracks_with_notes(tmp_path):
    composition = compose_music(build_spec())
    output = write_midi(composition, tmp_path / "multi_track.mid")
    midi = mido.MidiFile(str(output))
    note_tracks = [
        track
        for track in midi.tracks
        if any(msg.type == "note_on" for msg in track)
    ]
    assert len(note_tracks) >= 4
