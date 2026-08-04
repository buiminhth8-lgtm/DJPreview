"""局部重生成模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from services.api.schemas.music_spec import MusicSpec


class RegenerationRequest(BaseModel):
    scope: Literal["section", "track", "section_track", "overall"] = "section"
    section_id: str | None = None
    track_id: str | None = None
    instruction: str | None = None
    keep_harmony: bool = True
    keep_melody: bool = False
    keep_rhythm: bool = False
    variation_strength: float = Field(default=0.5, ge=0.0, le=1.0)
    seed_offset: int = Field(default=1, ge=0, le=1000)
    auto_render: bool = True


class RegenerationResult(BaseModel):
    song_id: str
    version_id: str
    parent_version_id: str
    music_spec: MusicSpec
    changed_targets: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    assets: dict = Field(default_factory=dict)
