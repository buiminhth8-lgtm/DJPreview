"""和声功能模型（T19）：功能、终止式与段落轮廓。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HarmonicFunction:
    """单个和弦的功能信息。"""

    name: str
    roman: str
    role: str  # tonic | predominant | dominant | color
    tension: float = 0.0


@dataclass(frozen=True)
class CadencePattern:
    """终止式模板（roman numeral，按调转换）。"""

    name: str
    chords: tuple[str, ...]
    strength: float


@dataclass(frozen=True)
class SectionHarmonyProfile:
    """段落和声轮廓参数。"""

    section_id: str
    cadence: str | None
    color_style: str | None = None
    tension: float = 0.0
