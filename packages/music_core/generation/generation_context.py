"""生成上下文。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GenerationContext:
    """Motif 渲染上下文。"""

    start_beat: float = 0.0
    root_pitch: int = 60
    velocity: int = 80
    channel: int = 0
    pitch_min: int = 55
    pitch_max: int = 88
    scale_degrees: list[int] = field(default_factory=list)
