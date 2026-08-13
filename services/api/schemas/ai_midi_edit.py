"""T35.1 Context and T35.4 Proposal transport contracts.

Data only: no route, LLM call, transformer invocation or persistence runtime.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from packages.music_core.midi_editing.models import MidiEditPlan, MidiEditScope
from packages.music_core.midi_editing.transformer import (
    MidiTransformWarningCode,
    canonical_note_key,
)
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


MidiNoteChangedField = Literal["pitch", "start_tick", "duration_tick", "velocity"]
_CHANGED_FIELD_ORDER = ("pitch", "start_tick", "duration_tick", "velocity")


class MidiNoteModification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    note_id: str = Field(min_length=1, max_length=200)
    before: MidiEditorNote
    after: MidiEditorNote
    changed_fields: tuple[MidiNoteChangedField, ...] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def _matches_note_values(self) -> MidiNoteModification:
        if self.before.id != self.note_id or self.after.id != self.note_id:
            raise ValueError("modification note_id 必须匹配 before/after")
        if self.before.channel != self.after.channel:
            raise ValueError("modification 不允许改变 channel")
        actual = tuple(
            field
            for field in _CHANGED_FIELD_ORDER
            if getattr(self.before, field) != getattr(self.after, field)
        )
        if self.changed_fields != actual:
            raise ValueError("changed_fields 必须精确匹配真实 Note 变化")
        return self


class AiMidiEditWarning(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: MidiTransformWarningCode
    operation_index: int = Field(ge=0, le=7)
    operation_type: str = Field(min_length=1, max_length=50)
    note_id: str = Field(min_length=1, max_length=200)


class AiMidiEditProposal(BaseModel):
    """Stateless scoped Proposal snapshot. This is not a Draft or Version."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=True,
    )

    proposal_id: UUID
    song_id: str = Field(min_length=1, max_length=200)
    base_version_id: str = Field(min_length=1, max_length=100)
    editor_session_id: UUID
    base_draft_revision: int = Field(ge=0)
    base_scope_revision: int = Field(ge=0)
    scope_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    track_id: str = Field(min_length=1, max_length=200)
    track_role: str | None = Field(default=None, max_length=100)
    scope: MidiEditScope
    transformer_seed: int = Field(ge=0, le=(2**32) - 1)

    planner_provider: str = Field(min_length=1, max_length=100)
    planner_model: str | None = Field(default=None, max_length=200)
    prompt_version: str = Field(min_length=1, max_length=100)
    plan: MidiEditPlan

    before_notes: list[MidiEditorNote] = Field(min_length=1, max_length=3000)
    after_notes: list[MidiEditorNote] = Field(min_length=1, max_length=3000)
    added: list[MidiEditorNote] = Field(default_factory=list, max_length=3000)
    deleted: list[MidiEditorNote] = Field(default_factory=list, max_length=3000)
    modified: list[MidiNoteModification] = Field(default_factory=list, max_length=3000)
    change_count: int = Field(ge=0, le=3000)
    is_noop: bool
    warnings: list[AiMidiEditWarning] = Field(default_factory=list, max_length=24000)
    created_at: datetime

    @model_validator(mode="after")
    def _internally_consistent(self) -> AiMidiEditProposal:
        if self.scope.track_id != self.track_id:
            raise ValueError("Proposal track_id 必须匹配 Scope")
        from packages.music_core.midi_editing.scope import scope_fingerprint

        if scope_fingerprint(self.scope) != self.scope_fingerprint:
            raise ValueError("Proposal scope_fingerprint 必须匹配 Scope")
        if self.before_notes != sorted(self.before_notes, key=canonical_note_key):
            raise ValueError("before_notes 必须使用 canonical order")
        if self.after_notes != sorted(self.after_notes, key=canonical_note_key):
            raise ValueError("after_notes 必须使用 canonical order")
        before_ids = [item.id for item in self.before_notes]
        after_ids = [item.id for item in self.after_notes]
        if len(before_ids) != len(set(before_ids)) or len(after_ids) != len(set(after_ids)):
            raise ValueError("Proposal Note ID 不能重复")
        before_by_id = {item.id: item for item in self.before_notes}
        after_by_id = {item.id: item for item in self.after_notes}
        before_set = set(before_by_id)
        after_set = set(after_by_id)
        if self.scope.type == "selected_notes" and before_set != set(self.scope.note_ids):
            raise ValueError("before_notes 必须精确匹配 selected_notes Scope")
        if self.scope.type in ("section", "tick_range") and any(
            not (self.scope.start_tick <= item.start_tick < self.scope.end_tick)
            for item in self.before_notes
        ):
            raise ValueError("before_notes 包含 Scope 时间窗外 Note")
        if not after_set <= before_set or self.added:
            raise ValueError("T35.3 Proposal 不允许 added Note")
        expected_deleted = [item for item in self.before_notes if item.id not in after_set]
        if self.deleted != expected_deleted:
            raise ValueError("deleted 必须精确匹配 before/after")
        changed_ids = {
            note_id
            for note_id in before_set & after_set
            if before_by_id[note_id] != after_by_id[note_id]
        }
        if [item.note_id for item in self.modified] != [
            item.id for item in self.after_notes if item.id in changed_ids
        ]:
            raise ValueError("modified 必须精确匹配 before/after")
        for item in self.modified:
            if item.before != before_by_id[item.note_id] or item.after != after_by_id[item.note_id]:
                raise ValueError("modified Note 值必须精确匹配 Proposal snapshot")
        expected_count = len(self.added) + len(self.deleted) + len(self.modified)
        if self.change_count != expected_count or self.is_noop != (expected_count == 0):
            raise ValueError("change_count/is_noop 与 Diff 不一致")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at 必须包含 timezone")
        for warning in self.warnings:
            if warning.note_id not in before_set:
                raise ValueError("warning note_id 必须属于 before_notes")
            if warning.operation_index >= len(self.plan.operations):
                raise ValueError("warning operation_index 超出 Plan")
            if self.plan.operations[warning.operation_index].type != warning.operation_type:
                raise ValueError("warning operation_type 必须匹配 Plan")
        return self
