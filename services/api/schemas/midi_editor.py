"""MIDI 编辑器文档模型（T34.1）。

Canonical 时间单位为 integer MIDI tick（T34.0 Final Decision）。
Track ID = MusicSpec track.id（稳定）；Note ID = deterministic hash（跨读取稳定）。
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class MidiEditorNote(BaseModel):
    """编辑器音符（tick 语义）。"""

    id: str
    pitch: int = Field(ge=0, le=127)
    start_tick: int = Field(ge=0)
    duration_tick: int = Field(gt=0)
    velocity: int = Field(ge=1, le=127)
    channel: int = Field(ge=0, le=15)

    @field_validator("start_tick")
    @classmethod
    def _start_not_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("start_tick 不能为负数")
        return value

    @field_validator("duration_tick")
    @classmethod
    def _duration_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("duration_tick 必须大于 0")
        return value


class MidiEditorTrack(BaseModel):
    """编辑器轨道。"""

    id: str
    role: str | None = None
    name: str
    channel: int = Field(ge=0, le=15)
    instrument: str | None = None
    is_drum: bool = False
    notes: list[MidiEditorNote] = Field(default_factory=list)


class MidiEditorDocument(BaseModel):
    """MIDI 编辑器文档（只读，T34.1）。"""

    song_id: str
    version_id: str | None = None
    ppq: int = Field(gt=0)
    bpm: int | None = None
    time_signature: tuple[int, int] = (4, 4)
    total_bars: float = 0.0
    tracks: list[MidiEditorTrack] = Field(default_factory=list)
