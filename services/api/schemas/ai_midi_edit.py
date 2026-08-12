"""T35 AI-assisted MIDI edit request and Context contracts.

T35.1 defines data only. No route, LLM call, transformer or proposal runtime.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from packages.music_core.midi_editing.models import MidiEditScope
from services.api.schemas.midi_editor import MidiEditorNote


class GenerateAiMidiEditProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    instruction: str = Field(min_length=1, max_length=1000)
    base_version_id: str = Field(min_length=1, max_length=100)
    editor_session_id: UUID
    draft_revision: int = Field(ge=0)
    scope_revision: int = Field(ge=0)
    scope: MidiEditScope
    draft_notes: list[MidiEditorNote] = Field(default_factory=list, max_length=3000)

    @field_validator("instruction")
    @classmethod
    def _strip_instruction(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("instruction 不能为空")
        return stripped


class AiMidiSectionContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str
    start_bar: int = Field(ge=1)
    bars: int = Field(ge=1)
    start_tick: int = Field(ge=0)
    end_tick: int = Field(gt=0)
    energy: float = Field(ge=0, le=1)


class AiMidiChordContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    section_id: str
    symbol: str
    bar: int = Field(ge=1)
    start_tick: int = Field(ge=0)
    end_tick: int = Field(gt=0)


class AiMidiEditContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    song_id: str
    base_version_id: str
    editor_session_id: UUID
    draft_revision: int = Field(ge=0)
    scope_revision: int = Field(ge=0)
    scope_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    scope: MidiEditScope

    track_id: str
    track_role: str | None = None
    instrument: str | None = None
    is_drum: bool
    channel_summary: list[int] = Field(default_factory=list)

    ppq: int = Field(gt=0)
    tempo_bpm: int | None = Field(default=None, gt=0)
    time_signature: tuple[int, int]
    total_ticks: int = Field(ge=0)
    scoped_notes: list[MidiEditorNote] = Field(default_factory=list, max_length=3000)

    key: str | None = None
    mode: str | None = None
    scale: str | None = None
    section: AiMidiSectionContext | None = None
    chords: list[AiMidiChordContext] = Field(default_factory=list, max_length=64)
