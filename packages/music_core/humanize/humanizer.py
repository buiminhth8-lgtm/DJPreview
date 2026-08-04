"""轻度人性化：对 NoteEvent 做可复现的微小时间/力度/时值变化。"""

from __future__ import annotations

import random

from packages.music_core.composer.events import NoteEvent


class Humanizer:
    """根据 seed 对音符做轻度人性化。"""

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def humanize(self, notes: list[NoteEvent], drum: bool = False) -> list[NoteEvent]:
        """返回新列表；鼓组变化幅度更小。"""
        if drum:
            start_jitter = 0.006
            vel_delta = 2
        else:
            start_jitter = 0.012
            vel_delta = 4

        result: list[NoteEvent] = []
        for note in notes:
            start = max(0.0, note.start_beat + self._rng.uniform(-start_jitter, start_jitter))
            duration = max(0.05, note.duration_beats + self._rng.uniform(-0.02, 0.02))
            velocity = max(1, min(127, note.velocity + self._rng.randint(-vel_delta, vel_delta)))
            result.append(
                NoteEvent(
                    pitch=note.pitch,
                    start_beat=round(start, 4),
                    duration_beats=round(duration, 4),
                    velocity=int(velocity),
                    channel=note.channel,
                    is_drum=note.is_drum,
                )
            )
        return result
