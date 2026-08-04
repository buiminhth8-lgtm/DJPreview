"""音频渲染器测试（不依赖系统 FluidSynth）。"""

import wave

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
