"""版本 index / metadata 数据模型（schema_version=2 目录式结构）。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class VersionMeta(BaseModel):
    """单版本元数据（写入 versions/vN/version_metadata.json）。"""

    version_id: str
    index: int
    parent_version_id: str | None = None
    created_at: str
    kind: str = "edit"  # initial / edit / regenerate / optimize
    prompt: str | None = None
    edit_instruction: str | None = None
    notes: str | None = None
    path: str = Field(description="相对项目目录的版本路径，例如 versions/v1")


class VersionIndexEntry(VersionMeta):
    """versions/index.json 中的版本条目（保留 version_number / instruction 兼容旧字段）。"""

    version_number: int
    instruction: str | None = None


class VersionIndex(BaseModel):
    """versions/index.json（schema_version=2）。"""

    schema_version: int = 2
    current_version_id: str | None = None
    versions: list[VersionIndexEntry] = Field(default_factory=list)
