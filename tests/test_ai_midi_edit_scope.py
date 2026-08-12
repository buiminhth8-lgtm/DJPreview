"""T35.1 strict Scope contracts and cross-language fingerprint fixtures."""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from packages.music_core.midi_editing.models import MidiEditScope
from packages.music_core.midi_editing.scope import (
    MidiEditScopeError,
    canonical_scope_json,
    scope_fingerprint,
    select_scoped_notes,
)
from services.api.schemas.midi_editor import MidiEditorNote

SCOPE_ADAPTER = TypeAdapter(MidiEditScope)


def note(note_id: str, start: int) -> MidiEditorNote:
    return MidiEditorNote(
        id=note_id,
        pitch=40,
        start_tick=start,
        duration_tick=120,
        velocity=90,
        channel=2,
    )


def test_scope_discriminated_union_accepts_all_four_types():
    scopes = [
        {"type": "selected_notes", "track_id": "bass", "note_ids": ["b1"]},
        {"type": "track", "track_id": "bass"},
        {
            "type": "section",
            "track_id": "bass",
            "section_id": "chorus",
            "start_tick": 1920,
            "end_tick": 3840,
        },
        {
            "type": "tick_range",
            "track_id": "bass",
            "start_tick": 0,
            "end_tick": 960,
        },
    ]
    assert [SCOPE_ADAPTER.validate_python(value).type for value in scopes] == [
        "selected_notes",
        "track",
        "section",
        "tick_range",
    ]


@pytest.mark.parametrize(
    "value",
    [
        {"type": "selected_notes", "track_id": "bass", "note_ids": []},
        {"type": "selected_notes", "track_id": "bass", "note_ids": ["b1", "b1"]},
        {"type": "track", "track_id": "bass", "note_ids": ["b1"]},
        {
            "type": "tick_range",
            "track_id": "bass",
            "start_tick": 960,
            "end_tick": 960,
        },
        {"type": "whole_song", "track_id": "bass"},
    ],
)
def test_scope_rejects_empty_duplicate_extra_invalid_range_and_unknown_type(value):
    with pytest.raises(ValidationError):
        SCOPE_ADAPTER.validate_python(value)


def test_selected_notes_membership_must_match_exactly():
    scope = SCOPE_ADAPTER.validate_python(
        {"type": "selected_notes", "track_id": "bass", "note_ids": ["b1", "b2"]}
    )
    selected = select_scoped_notes(scope, [note("b2", 120), note("b1", 0)])
    assert [item.id for item in selected] == ["b1", "b2"]

    with pytest.raises(MidiEditScopeError, match="missing"):
        select_scoped_notes(scope, [note("b1", 0)])
    with pytest.raises(MidiEditScopeError, match="extra"):
        select_scoped_notes(scope, [note("b1", 0), note("b2", 120), note("b3", 240)])


def test_time_scope_uses_half_open_start_tick_membership():
    scope = SCOPE_ADAPTER.validate_python(
        {
            "type": "tick_range",
            "track_id": "bass",
            "start_tick": 480,
            "end_tick": 960,
        }
    )
    selected = select_scoped_notes(scope, [note("inside", 480), note("last", 959)])
    assert [item.id for item in selected] == ["inside", "last"]
    with pytest.raises(MidiEditScopeError, match="范围外"):
        select_scoped_notes(scope, [note("end", 960)])


def test_duplicate_supplied_note_ids_are_rejected():
    scope = SCOPE_ADAPTER.validate_python({"type": "track", "track_id": "bass"})
    with pytest.raises(MidiEditScopeError, match="重复"):
        select_scoped_notes(scope, [note("b1", 0), note("b1", 480)])


def test_selected_scope_canonical_json_and_fingerprint_are_frozen_for_typescript():
    scope = SCOPE_ADAPTER.validate_python(
        {"type": "selected_notes", "track_id": "bass", "note_ids": ["b2", "b1"]}
    )
    assert canonical_scope_json(scope) == (
        '{"type":"selected_notes","trackId":"bass","noteIds":["b1","b2"]}'
    )
    assert scope_fingerprint(scope) == (
        "ac22ebf675cca80ab382b8cb347d0d8e57127ff9052eaf121ba55fe1bb59df66"
    )


@pytest.mark.parametrize(
    ("value", "canonical", "fingerprint"),
    [
        (
            {"type": "track", "track_id": "bass"},
            '{"type":"track","trackId":"bass"}',
            "95713958c4a25ceb8c2b000c2f8ac314575024dd08415f59cf5bb09ddaddb41d",
        ),
        (
            {
                "type": "section",
                "track_id": "bass",
                "section_id": "chorus",
                "start_tick": 3840,
                "end_tick": 7680,
            },
            '{"type":"section","trackId":"bass","sectionId":"chorus","startTick":3840,"endTick":7680}',
            "4689cd3055240c5f7234784fb7f9d3a2a0fce645af842e1ae31b027f1d8fb712",
        ),
        (
            {
                "type": "tick_range",
                "track_id": "bass",
                "start_tick": 480,
                "end_tick": 960,
            },
            '{"type":"tick_range","trackId":"bass","startTick":480,"endTick":960}',
            "289f97cdc91aeacb3613350cf8d5904f6b036c77ea328f358d46c865ce48f536",
        ),
    ],
)
def test_other_scope_fingerprints_are_frozen_for_typescript(value, canonical, fingerprint):
    scope = SCOPE_ADAPTER.validate_python(value)
    assert canonical_scope_json(scope) == canonical
    assert scope_fingerprint(scope) == fingerprint
