"""Canonical T35 MIDI edit Scope and Plan contracts.

Scope is the authorization boundary. LLM plans never own or expand it.
"""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class _StrictOperation(BaseModel):
    """Closed operation schema: no coercion, non-finite number or extension field."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
    )


class TransposeMidiEditOperation(_StrictOperation):
    type: Literal["transpose"]
    semitones: int = Field(ge=-24, le=24)

    @field_validator("semitones")
    @classmethod
    def _reject_noop(cls, value: int) -> int:
        if value == 0:
            raise ValueError("semitones 不能为 0")
        return value


class OctaveShiftMidiEditOperation(_StrictOperation):
    type: Literal["octave_shift"]
    octaves: int = Field(ge=-2, le=2)

    @field_validator("octaves")
    @classmethod
    def _reject_noop(cls, value: int) -> int:
        if value == 0:
            raise ValueError("octaves 不能为 0")
        return value


class VelocitySetMidiEditOperation(_StrictOperation):
    type: Literal["velocity_set"]
    value: int = Field(ge=1, le=127)


class VelocityDeltaMidiEditOperation(_StrictOperation):
    type: Literal["velocity_delta"]
    delta: int = Field(ge=-64, le=64)

    @field_validator("delta")
    @classmethod
    def _reject_noop(cls, value: int) -> int:
        if value == 0:
            raise ValueError("delta 不能为 0")
        return value


class VelocityScaleMidiEditOperation(_StrictOperation):
    type: Literal["velocity_scale"]
    factor: float = Field(ge=0.25, le=2.0)

    @field_validator("factor")
    @classmethod
    def _reject_noop(cls, value: float) -> float:
        if value == 1:
            raise ValueError("factor 不能为 1")
        return value


class DurationScaleMidiEditOperation(_StrictOperation):
    type: Literal["duration_scale"]
    factor: float = Field(ge=0.25, le=4.0)

    @field_validator("factor")
    @classmethod
    def _reject_noop(cls, value: float) -> float:
        if value == 1:
            raise ValueError("factor 不能为 1")
        return value


class StaccatoMidiEditOperation(_StrictOperation):
    type: Literal["staccato"]
    ratio: float = Field(ge=0.10, le=0.95)


class LegatoMidiEditOperation(_StrictOperation):
    type: Literal["legato"]
    overlap_ticks: int = Field(default=0, ge=0, le=1920)


QuantizeGrid: TypeAlias = Literal["1/4", "1/8", "1/16", "1/32"]


class QuantizeMidiEditOperation(_StrictOperation):
    type: Literal["quantize"]
    grid: QuantizeGrid
    strength: float = Field(default=1.0, gt=0, le=1.0)


class ShiftTimingMidiEditOperation(_StrictOperation):
    type: Literal["shift_timing"]
    delta_ticks: int

    @field_validator("delta_ticks")
    @classmethod
    def _reject_noop(cls, value: int) -> int:
        if value == 0:
            raise ValueError("delta_ticks 不能为 0")
        return value


class ReduceDensityMidiEditOperation(_StrictOperation):
    type: Literal["reduce_density"]
    keep_ratio: float = Field(ge=0.10, le=0.95)
    preserve_edges: bool = True


MidiEditOperation: TypeAlias = Annotated[
    TransposeMidiEditOperation
    | OctaveShiftMidiEditOperation
    | VelocitySetMidiEditOperation
    | VelocityDeltaMidiEditOperation
    | VelocityScaleMidiEditOperation
    | DurationScaleMidiEditOperation
    | StaccatoMidiEditOperation
    | LegatoMidiEditOperation
    | QuantizeMidiEditOperation
    | ShiftTimingMidiEditOperation
    | ReduceDensityMidiEditOperation,
    Field(discriminator="type"),
]


class MidiEditPlan(BaseModel):
    """Ordered, scope-free instructions proposed by an AI planner."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )

    schema_version: Literal["1.0"]
    summary: str = Field(min_length=1, max_length=200)
    operations: list[MidiEditOperation] = Field(min_length=1, max_length=8)
