"""Stable, fail-closed note diff for T35.4 AI MIDI edit Proposals."""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from enum import StrEnum

from pydantic import ValidationError

from packages.music_core.midi_editing.transformer import canonical_note_key
from services.api.schemas.midi_editor import MidiEditorNote

NOTE_DIFF_FIELDS = ("pitch", "start_tick", "duration_tick", "velocity")


class MidiNoteDiffErrorCode(StrEnum):
    INVALID_NOTES = "invalid_notes"
    DUPLICATE_NOTE_ID = "duplicate_note_id"
    UNKNOWN_AFTER_ID = "unknown_after_id"
    SCOPE_VIOLATION = "scope_violation"
    CHANNEL_CHANGED = "channel_changed"


class MidiNoteDiffError(ValueError):
    """A diff cannot be trusted as an authorized Proposal change set."""

    def __init__(
        self,
        code: MidiNoteDiffErrorCode,
        message: str,
        *,
        note_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.note_id = note_id


@dataclass(frozen=True)
class MidiNoteModificationDiff:
    note_id: str
    before: MidiEditorNote
    after: MidiEditorNote
    changed_fields: tuple[str, ...]


@dataclass(frozen=True)
class MidiNoteDiff:
    before_notes: tuple[MidiEditorNote, ...]
    after_notes: tuple[MidiEditorNote, ...]
    added: tuple[MidiEditorNote, ...]
    deleted: tuple[MidiEditorNote, ...]
    modified: tuple[MidiNoteModificationDiff, ...]

    @property
    def change_count(self) -> int:
        return len(self.added) + len(self.deleted) + len(self.modified)

    @property
    def is_noop(self) -> bool:
        return self.change_count == 0


def _validated_notes(
    notes: Sequence[MidiEditorNote],
    *,
    label: str,
) -> tuple[MidiEditorNote, ...]:
    copied: list[MidiEditorNote] = []
    try:
        for item in notes:
            if not isinstance(item, MidiEditorNote):
                raise TypeError("note type")
            copied.append(
                MidiEditorNote.model_validate(item.model_dump(mode="python"), strict=True)
            )
    except (TypeError, ValidationError, ValueError) as error:
        raise MidiNoteDiffError(
            MidiNoteDiffErrorCode.INVALID_NOTES,
            f"{label} 包含非法 Note",
        ) from error
    ids = [item.id for item in copied]
    if len(ids) != len(set(ids)):
        raise MidiNoteDiffError(
            MidiNoteDiffErrorCode.DUPLICATE_NOTE_ID,
            f"{label} 包含重复 Note ID",
        )
    return tuple(sorted(copied, key=canonical_note_key))


def calculate_midi_note_diff(
    before_notes: Sequence[MidiEditorNote],
    after_notes: Sequence[MidiEditorNote],
    *,
    authorized_note_ids: Collection[str],
) -> MidiNoteDiff:
    """Compare stable IDs in O(n log n), rejecting all T35.3 additions."""
    before = _validated_notes(before_notes, label="before_notes")
    after = _validated_notes(after_notes, label="after_notes")
    authorized_ids = set(authorized_note_ids)
    if len(authorized_ids) != len(authorized_note_ids):
        raise MidiNoteDiffError(
            MidiNoteDiffErrorCode.DUPLICATE_NOTE_ID,
            "authorized_note_ids 包含重复 Note ID",
        )

    before_by_id = {item.id: item for item in before}
    after_by_id = {item.id: item for item in after}
    before_ids = set(before_by_id)
    after_ids = set(after_by_id)
    outside_before = before_ids - authorized_ids
    if outside_before:
        raise MidiNoteDiffError(
            MidiNoteDiffErrorCode.SCOPE_VIOLATION,
            "before_notes 包含 Scope 外 Note ID",
            note_id=min(outside_before),
        )
    outside_after = after_ids - authorized_ids
    if outside_after:
        raise MidiNoteDiffError(
            MidiNoteDiffErrorCode.SCOPE_VIOLATION,
            "after_notes 包含 Scope 外 Note ID",
            note_id=min(outside_after),
        )

    added_ids = after_ids - before_ids
    if added_ids:
        raise MidiNoteDiffError(
            MidiNoteDiffErrorCode.UNKNOWN_AFTER_ID,
            "T35.3 Transformer 不允许新增 Note ID",
            note_id=min(added_ids),
        )

    deleted = tuple(
        item for item in before if item.id in before_ids - after_ids
    )
    modifications: list[MidiNoteModificationDiff] = []
    for after_item in after:
        before_item = before_by_id[after_item.id]
        if after_item.channel != before_item.channel:
            raise MidiNoteDiffError(
                MidiNoteDiffErrorCode.CHANNEL_CHANGED,
                "Transformer 修改 channel 不能作为普通 diff",
                note_id=after_item.id,
            )
        changed_fields = tuple(
            field
            for field in NOTE_DIFF_FIELDS
            if getattr(before_item, field) != getattr(after_item, field)
        )
        if changed_fields:
            modifications.append(
                MidiNoteModificationDiff(
                    note_id=after_item.id,
                    before=before_item.model_copy(deep=True),
                    after=after_item.model_copy(deep=True),
                    changed_fields=changed_fields,
                )
            )

    return MidiNoteDiff(
        before_notes=before,
        after_notes=after,
        added=(),
        deleted=deleted,
        modified=tuple(modifications),
    )
