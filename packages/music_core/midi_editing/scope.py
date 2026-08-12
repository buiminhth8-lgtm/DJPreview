"""Non-LLM MIDI scope validation, selection and canonical fingerprinting."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

from packages.music_core.midi_editing.models import MidiEditScope
from services.api.schemas.midi_editor import MidiEditorNote


class MidiEditScopeError(ValueError):
    """A client scope or its note membership is invalid."""


def canonical_scope_dict(scope: MidiEditScope) -> dict[str, object]:
    """Return the cross-language canonical camelCase scope representation."""
    if scope.type == "selected_notes":
        return {
            "type": scope.type,
            "trackId": scope.track_id,
            "noteIds": sorted(scope.note_ids),
        }
    if scope.type == "track":
        return {"type": scope.type, "trackId": scope.track_id}
    if scope.type == "section":
        return {
            "type": scope.type,
            "trackId": scope.track_id,
            "sectionId": scope.section_id,
            "startTick": scope.start_tick,
            "endTick": scope.end_tick,
        }
    return {
        "type": scope.type,
        "trackId": scope.track_id,
        "startTick": scope.start_tick,
        "endTick": scope.end_tick,
    }


def canonical_scope_json(scope: MidiEditScope) -> str:
    return json.dumps(
        canonical_scope_dict(scope),
        ensure_ascii=False,
        separators=(",", ":"),
    )


def scope_fingerprint(scope: MidiEditScope) -> str:
    return hashlib.sha256(canonical_scope_json(scope).encode("utf-8")).hexdigest()


def validate_unique_notes(notes: Sequence[MidiEditorNote]) -> None:
    note_ids = [note.id for note in notes]
    if len(note_ids) != len(set(note_ids)):
        raise MidiEditScopeError("draft_notes 包含重复 note ID")


def select_scoped_notes(
    scope: MidiEditScope,
    notes: Sequence[MidiEditorNote],
) -> list[MidiEditorNote]:
    """Validate and copy the client-declared authorized note set.

    Omitting notes can only narrow authority. Supplying an out-of-scope note is
    rejected, and selected_notes must match the declared IDs exactly.
    """
    validate_unique_notes(notes)
    copied = [note.model_copy(deep=True) for note in notes]
    if scope.type == "selected_notes":
        requested = set(scope.note_ids)
        supplied = {note.id for note in copied}
        if supplied != requested:
            missing = sorted(requested - supplied)
            extra = sorted(supplied - requested)
            raise MidiEditScopeError(
                f"selected_notes membership 不一致（missing={missing}, extra={extra}）"
            )
    elif scope.type in ("section", "tick_range"):
        outside = [
            note.id
            for note in copied
            if not (scope.start_tick <= note.start_tick < scope.end_tick)
        ]
        if outside:
            raise MidiEditScopeError(
                f"draft_notes 包含时间范围外 Note：{', '.join(sorted(outside))}"
            )
    return sorted(
        copied,
        key=lambda note: (note.start_tick, note.pitch, note.channel, note.id),
    )
