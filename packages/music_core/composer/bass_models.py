"""贝斯事件模型（T21）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BassNote:
    """单个贝斯音。role：root / fifth / octave / passing / approach / ghost。"""

    time_beats: float
    duration_beats: float
    pitch: int
    velocity: int
    role: str = "root"
