"""MixSpec / TrackMixSpec 数据模型（Pydantic v2）。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TrackMixSpec(BaseModel):
    """单轨混音参数。"""

    track_id: str = Field(min_length=1)
    role: str | None = None
    volume: float = Field(default=1.0, ge=0.0, le=1.5, description="音量（近似通过 velocity 实现）")
    pan: float = Field(default=0.0, ge=-1.0, le=1.0, description="声像 -1(左) ~ 1(右)")
    mute: bool = False
    solo: bool = False
    enabled: bool = True
    velocity_scale: float = Field(default=1.0, ge=0.1, le=2.0, description="力度缩放")
    program: int | None = Field(default=None, description="GM program，None 表示跟随 MusicSpec")
    instrument: str | None = None


class MixSpec(BaseModel):
    """整曲混音方案。"""

    version: str = "0.1"
    song_id: str | None = None
    version_id: str | None = None
    master_volume: float = Field(default=1.0, ge=0.0, le=1.5)
    tracks: list[TrackMixSpec] = Field(default_factory=list)
    notes: str | None = None
