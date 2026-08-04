"""StyleTemplateSpec —— 风格模板数据模型（Pydantic v2）。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StyleTemplateSpec(BaseModel):
    """生成 MusicSpec 前的高级风格约束，不是最终 MusicSpec 的替代品。"""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    default_tempo: int | None = None
    tempo_range: tuple[int, int] | None = None
    preferred_keys: list[str] = Field(default_factory=list)
    preferred_modes: list[str] = Field(default_factory=list)
    preferred_scales: list[str] = Field(default_factory=list)
    default_meter: str = "4/4"
    default_length_bars: int = 32
    default_form: list[dict] = Field(default_factory=list)
    default_tracks: list[dict] = Field(default_factory=list)
    harmony_presets: list[list[str]] = Field(default_factory=list)
    rhythm_presets: list[str] = Field(default_factory=list)
    melody_profile: dict = Field(default_factory=dict)
    arrangement_curve: dict = Field(default_factory=dict)
    mix_hints: dict | None = None
    notes: str | None = None
