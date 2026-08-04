"""鼓组事件模型（T20）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DrumHit:
    """单个鼓组击打。"""

    time_beats: float
    duration_beats: float
    note: int
    velocity: int
    label: str
