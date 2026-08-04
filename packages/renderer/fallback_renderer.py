"""Fallback 渲染器：无 FluidSynth 时的开发兜底，生成可试听、可测试的 WAV。"""

from __future__ import annotations

import logging
import wave
from pathlib import Path

import mido
import numpy as np

from packages.renderer.audio_metadata import AudioRenderResult, get_wav_duration_seconds

logger = logging.getLogger(__name__)

# A4 = 440Hz，MIDI 69
_A4_MIDI = 69
_A4_FREQ = 440.0


def midi_to_freq(midi: int) -> float:
    """MIDI 音高 → 频率（Hz）。"""
    return _A4_FREQ * (2.0 ** ((midi - _A4_MIDI) / 12.0))


def _collect_notes(midi_path: Path) -> tuple[float, list[tuple[float, float, float, float]]]:
    """解析 MIDI，返回 (总时长秒, notes)；notes 为 (start_sec, dur_sec, freq, velocity_scale)。"""
    midi = mido.MidiFile(str(midi_path))
    tpb = midi.ticks_per_beat or 480
    tempo = 500000  # 默认 120 BPM
    notes: list[tuple[float, float, float, float]] = []

    for track in midi.tracks:
        tick = 0
        active: dict[int, int] = {}
        for msg in track:
            tick += msg.time
            if msg.type == "set_tempo":
                tempo = msg.tempo
            elif msg.type == "note_on" and msg.velocity > 0:
                active[msg.note] = tick
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                start_tick = active.pop(msg.note, None)
                if start_tick is None:
                    continue
                start_sec = start_tick / tpb * tempo / 1_000_000
                dur_sec = max(0.05, (tick - start_tick) / tpb * tempo / 1_000_000)
                notes.append((start_sec, dur_sec, midi_to_freq(msg.note), msg.velocity / 127.0))

    notes.sort(key=lambda item: item[0])
    total_seconds = max((n[0] + n[1] for n in notes), default=0.0) + 1.0
    return total_seconds, notes


class FallbackRenderer:
    """开发兜底渲染器：sine/triangle 合成，多音符叠加，输出合法 WAV。"""

    name = "fallback"

    def render_wav(
        self,
        midi_path: Path,
        wav_path: Path,
        *,
        sample_rate: int = 44100,
        gain: float = 0.6,
    ) -> AudioRenderResult:
        total_seconds, notes = _collect_notes(Path(midi_path))
        if not notes:
            total_seconds = 1.0

        n_samples = int(total_seconds * sample_rate) + 1
        mix = np.zeros(n_samples, dtype=np.float64)

        for start_sec, dur_sec, freq, vel in notes:
            s0 = int(start_sec * sample_rate)
            if s0 >= n_samples:
                continue
            length = int(dur_sec * sample_rate)
            end = min(s0 + length, n_samples)
            t = np.arange(end - s0) / sample_rate
            # 三角波近似（能清晰听到音高）+ 指数衰减包络
            waveform = 2.0 * np.abs(2.0 * ((freq * t) % 1.0) - 1.0) - 1.0
            envelope = np.exp(-2.5 * t / max(dur_sec, 0.1))
            mix[s0:end] += waveform * envelope * (0.10 + 0.20 * vel)

        peak = float(np.max(np.abs(mix))) if n_samples else 0.0
        if peak > 0.0:
            mix = mix / peak * gain
        pcm = (mix * 32767.0).astype(np.int16)

        wav_path = Path(wav_path)
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(wav_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(pcm.tobytes())

        return AudioRenderResult(
            wav_path=wav_path,
            renderer=self.name,
            sample_rate=sample_rate,
            duration_seconds=get_wav_duration_seconds(wav_path),
            file_size=wav_path.stat().st_size,
            warnings=[
                "使用 fallback 渲染器（开发兜底，正式音质请安装 FluidSynth + SoundFont）"
            ],
        )
