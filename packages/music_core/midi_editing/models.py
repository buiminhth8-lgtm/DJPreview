"""T35 MIDI edit scope contracts.

Scope is the authorization boundary. LLM plans never own or expand it.
"""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _StrictScope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


NoteId: TypeAlias = Annotated[
    str,
    Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9:_-]+$"),
]


class SelectedNotesMidiEditScope(_StrictScope):
    type: Literal["selected_notes"] = "selected_notes"
    track_id: str = Field(min_length=1, max_length=200)
    note_ids: list[NoteId] = Field(min_length=1, max_length=3000)

    @model_validator(mode="after")
    def _unique_note_ids(self) -> SelectedNotesMidiEditScope:
        if len(self.note_ids) != len(set(self.note_ids)):
            raise ValueError("note_ids 不能重复")
        return self


class TrackMidiEditScope(_StrictScope):
    type: Literal["track"] = "track"
    track_id: str = Field(min_length=1, max_length=200)


class SectionMidiEditScope(_StrictScope):
    type: Literal["section"] = "section"
    track_id: str = Field(min_length=1, max_length=200)
    section_id: str = Field(min_length=1, max_length=200)
    start_tick: int = Field(ge=0)
    end_tick: int = Field(gt=0)

    @model_validator(mode="after")
    def _ordered_range(self) -> SectionMidiEditScope:
        if self.end_tick <= self.start_tick:
            raise ValueError("end_tick 必须大于 start_tick")
        return self


class TickRangeMidiEditScope(_StrictScope):
    type: Literal["tick_range"] = "tick_range"
    track_id: str = Field(min_length=1, max_length=200)
    start_tick: int = Field(ge=0)
    end_tick: int = Field(gt=0)

    @model_validator(mode="after")
    def _ordered_range(self) -> TickRangeMidiEditScope:
        if self.end_tick <= self.start_tick:
            raise ValueError("end_tick 必须大于 start_tick")
        return self


MidiEditScope: TypeAlias = Annotated[
    SelectedNotesMidiEditScope
    | TrackMidiEditScope
    | SectionMidiEditScope
    | TickRangeMidiEditScope,
    Field(discriminator="type"),
]
