"""SoundFont 数据模型（T29）。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SoundFontInfo(BaseModel):
    """单个 SoundFont 音源信息。"""

    id: str
    name: str
    path: str
    format: str  # sf2 / sf3 / sfz
    size_bytes: int
    is_default: bool = False
    tags: list[str] = Field(default_factory=list)
