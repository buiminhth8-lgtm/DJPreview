"""音频渲染器测试（不依赖系统 FluidSynth）。"""

import wave

import mido

from packages.music_core.composer.music_composer import compose_music
from packages.music_core.midi.midi_writer import write_midi
from packages.renderer.audio_metadata import get_wav_duration_seconds
from packages.renderer.fallback_renderer import FallbackRenderer
from tests.test_harmony_engine import build_spec


def _make_midi(tmp_path) -> str:
    spec = build_spec()
    midi_path = write_midi(compose_music(spec), tmp_path / "input.mid")
    return str(midi_path)


def test_fallback_renderer_creates_wav(tmp_path):
    midi_path = _make_midi(tmp_path)
    wav_path = tmp_path / "output.wav"
    result = FallbackRenderer().render_wav(midi_path, wav_path, sample_rate=8000, gain=0.6)

    assert result.wav_path.exists()
    assert result.renderer == "fallback"
    assert result.file_size > 0
    assert result.sample_rate == 8000


def test_wav_is_valid_and_has_duration(tmp_path):
    midi_path = _make_midi(tmp_path)
    wav_path = tmp_path / "output.wav"
    FallbackRenderer().render_wav(midi_path, wav_path, sample_rate=8000, gain=0.6)

    with wave.open(str(wav_path), "rb") as wav:
        assert wav.getnframes() > 0
        assert wav.getframerate() == 8000
        assert wav.getsampwidth() == 2

    duration = get_wav_duration_seconds(wav_path)
    assert duration is not None
    assert duration > 0


def _overlap_midi(tmp_path) -> str:
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
    return str(path)


def test_fallback_renderer_handles_overlapping_same_note(tmp_path):
    """T16：fallback renderer 可渲染同音高重叠音符的 MIDI。"""
    midi_path = _overlap_midi(tmp_path)
    wav_path = tmp_path / "overlap.wav"
    result = FallbackRenderer().render_wav(midi_path, wav_path, sample_rate=8000, gain=0.6)

    assert result.wav_path.exists()
    assert result.file_size > 0
    assert result.duration_seconds is not None
    assert result.duration_seconds > 0
    with wave.open(str(wav_path), "rb") as wav:
        assert wav.getnframes() > 0
        assert wav.getsampwidth() == 2


def test_fallback_renderer_handles_edge_midi(tmp_path):
    """T16：未配对 note_off / note_on velocity=0 / 未关闭 note_on 均不崩溃。"""
    midi = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    track.append(mido.Message("note_off", note=64, velocity=0, time=0, channel=0))  # 未配对
    track.append(mido.Message("note_on", note=60, velocity=80, time=0, channel=0))
    track.append(mido.Message("note_on", note=60, velocity=0, time=240, channel=0))  # vel=0 → note_off
    track.append(mido.Message("note_on", note=67, velocity=80, time=0, channel=0))  # 未关闭
    track.append(mido.MetaMessage("end_of_track"))
    midi.tracks.append(track)
    path = tmp_path / "edge.mid"
    midi.save(str(path))

    wav_path = tmp_path / "edge.wav"
    result = FallbackRenderer().render_wav(str(path), wav_path, sample_rate=8000, gain=0.6)
    assert result.wav_path.exists()
    assert result.file_size > 0
    assert result.duration_seconds is not None
    assert result.duration_seconds > 0
