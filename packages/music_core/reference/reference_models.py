"""参考 MIDI 分析模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReferenceMidiAnalysis(BaseModel):
    """从参考 MIDI 提取的高层特征（不包含原始旋律音符）。"""

    file_name: str
    ticks_per_beat: int
    bpm: int | None = None
    estimated_bars: float = 0.0
    track_count: int = 0
    note_count: int = 0
    pitch_range: dict = Field(default_factory=dict)
    density: dict = Field(default_factory=dict)
    rhythm_profile: dict = Field(default_factory=dict)
    energy_curve: list[dict] = Field(default_factory=list)
    track_summaries: list[dict] = Field(default_factory=list)
    possible_roles: list[str] = Field(default_factory=list)
    suggested_style_tags: list[str] = Field(default_factory=list)
    suggested_tempo_range: tuple[int, int] | None = None
    suggested_tracks: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
