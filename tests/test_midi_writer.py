"""MIDI Writer 测试。"""

import mido

from packages.music_core.composer.music_composer import compose_music
from packages.music_core.midi.midi_writer import write_midi
from services.api.schemas.music_spec import TrackSpec
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


def _spec_with_instruments():
    spec = build_spec()
    spec.tracks = [
        TrackSpec(id="melody", role="melody", instrument="acoustic_grand_piano", velocity=90),
        TrackSpec(id="bass", role="bass", instrument="electric_bass_finger", velocity=90),
        TrackSpec(id="strings", role="pad", instrument="string_ensemble_1", velocity=70),
        TrackSpec(id="drums", role="drums", instrument="standard_drum_kit", velocity=100),
        TrackSpec(id="mystery", role="harmony", instrument="unknown_xyz", velocity=70),
    ]
    return spec


def test_program_change_uses_registry_mapping(tmp_path):
    """T17：piano=0 / bass=33 / strings=48 / drums=channel 9 / unknown 回退 0。"""
    composition = compose_music(_spec_with_instruments())
    output = write_midi(composition, tmp_path / "programs.mid")
    programs: dict[int, int] = {}
    drum_channels: set[int] = set()
    for track in mido.MidiFile(str(output)).tracks:
        for msg in track:
            if msg.type == "program_change":
                programs[msg.channel] = msg.program
            elif msg.type == "note_on":
                drum_channels.add(msg.channel)

    assert programs.get(0) == 0  # melody acoustic_grand_piano
    assert programs.get(2) == 33  # electric_bass_finger
    assert programs.get(3) == 48  # string_ensemble_1（pad 通道 3）
    assert programs.get(1) == 0  # unknown → fallback program 0
    assert 9 not in programs  # 鼓组不写 melodic program
    assert 9 in drum_channels  # 鼓组使用 MIDI channel 9


def test_drum_track_uses_gm_notes(tmp_path):
    """T20：drums 轨道只使用 GM drum note，并走 channel 9。"""
    from packages.music_core.midi.midi_constants import DRUM_NOTES

    composition = compose_music(_spec_with_instruments())
    output = write_midi(composition, tmp_path / "drums_gm.mid")
    gm_notes = set(DRUM_NOTES.values())
    drum_note_on = 0
    for track in mido.MidiFile(str(output)).tracks:
        for msg in track:
            if msg.type == "note_on" and msg.channel == 9:
                drum_note_on += 1
                assert msg.note in gm_notes
    assert drum_note_on > 0
