"""MusicEditSpec v0.1 —— 音乐修改协议。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class EditTarget(BaseModel):
    """修改作用目标。"""

    section: str | None = Field(default=None, description="目标段落 id")
    track: str | None = Field(default=None, description="目标轨道 id")
    scope: Literal["overall", "section", "track", "partial"] = Field(
        default="partial", description="作用范围：整体 / 段落 / 轨道 / 局部"
    )


class EditOperation(BaseModel):
    """单条修改操作。"""

    type: str = Field(min_length=1, description="操作类型，例如 tempo、tonality、velocity、instrument")
    amount: float | None = Field(default=None, description="增量数值")
    value: str | int | float | bool | None = Field(default=None, description="目标值")
    params: dict[str, Any] | None = Field(default=None, description="额外参数")


class MusicEditSpec(BaseModel):
    """MusicEditSpec v0.1 —— 对已有 MusicSpec 的修改指令。"""

    version: str = Field(default="0.1", description="协议版本")
    instruction: str = Field(min_length=1, description="原始修改指令")
    target: EditTarget
    preserve: list[str] = Field(default_factory=list, description="需保持不变（或不可修改）的字段")
    operations: list[EditOperation] = Field(default_factory=list, description="修改操作列表")
