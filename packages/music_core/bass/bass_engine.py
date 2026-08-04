"""贝斯引擎：基于和弦根音生成贝斯声部。"""

from __future__ import annotations

import random

from packages.music_core.composer.events import NoteEvent, beats_per_bar, section_energy
from packages.music_core.harmony.harmony_engine import BarHarmony
from services.api.schemas.music_spec import MusicSpec

_BASS_MIN = 36
_BASS_MAX = 52


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _bass_root(chord_pitches: list[int]) -> int:
    """把和弦根音放到 [36, 52] 内的最低可用八度。

    例如 C4=60 -> C2=36，G3=55 -> G2=43，Bb4=70 -> Bb2=46。
    避免直接 clamp 导致 G/Am 等低根音被错误钳成 C。
    """
    root = chord_pitches[0] if chord_pitches else 60
    while root - 12 >= _BASS_MIN:
        root -= 12
    return _clamp(root, _BASS_MIN, _BASS_MAX)


class BassEngine:
    """生成贝斯轨道：强拍根音，energy 高时增加节奏密度。"""

    def generate(
        self,
        music_spec: MusicSpec,
        bar_harmony: list[BarHarmony],
        channel: int = 2,
    ) -> list[NoteEvent]:
        rng = random.Random(music_spec.seed + 7)
        bpb = beats_per_bar(music_spec)
        notes: list[NoteEvent] = []

        for bar in bar_harmony:
            energy = section_energy(music_spec, bar.section_id)
            bar_start = (bar.bar_index - 1) * bpb
            root = _bass_root(bar.chord_pitches)
            # 五度优先向上取 root+7；超出音域时取低八度五度 root-5
            fifth = root + 7 if root + 7 <= _BASS_MAX else root - 5
            velocity = int(66 + energy * 30)

            if energy < 0.4:
                hits = [(0.0, 3.5, root, 1.0)]
            elif energy < 0.7:
                hits = [
                    (0.0, 1.5, root, 1.0),
                    (2.0, 1.5, root, 0.85),
                ]
            else:
                hits = [
                    (0.0, 0.9, root, 1.0),
                    (1.0, 0.8, fifth, 0.8),
                    (2.0, 0.9, root, 0.95),
                    (3.0, 0.8, fifth if rng.random() < 0.5 else root, 0.8),
                ]

            for beat, duration, pitch, vel_scale in hits:
                notes.append(
                    NoteEvent(
                        pitch=_clamp(pitch, 0, 127),
                        start_beat=round(bar_start + beat, 3),
                        duration_beats=round(duration, 3),
                        velocity=_clamp(int(velocity * vel_scale), 1, 127),
                        channel=channel,
                    )
                )
        return notes
