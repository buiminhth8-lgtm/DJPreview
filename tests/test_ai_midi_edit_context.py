"""T35.1 authoritative Context construction and prompt compaction."""

from __future__ import annotations

import json
from uuid import UUID

import pytest

from services.api.schemas.ai_midi_edit import GenerateAiMidiEditProposalRequest
from services.api.schemas.midi_editor import (
    MidiEditorDocument,
    MidiEditorNote,
    MidiEditorTrack,
)
from services.api.schemas.music_spec import (
    HarmonySectionSpec,
    LengthSpec,
    MeterSpec,
    MusicSpec,
    SectionSpec,
    TempoSpec,
    TonalitySpec,
    TrackSpec,
)
from services.api.services.ai_midi_edit_context import (
    MAX_EXACT_PLANNER_NOTES,
    AiMidiEditContextError,
    build_ai_midi_edit_context,
    build_planner_payload,
)
from packages.music_core.midi_editing.scope import MidiEditScopeError

SESSION_ID = UUID("8d2cf52d-c4d4-4f5a-87e7-1b5860c7a663")


def make_spec() -> MusicSpec:
    return MusicSpec(
        title="Context",
        seed=1,
        prompt="secret original prompt",
        tempo=TempoSpec(bpm=120),
        meter=MeterSpec(numerator=4, denominator=4),
        tonality=TonalitySpec(key="C", mode="major", scale="c-major"),
        length=LengthSpec(bars=4),
        form=[
            SectionSpec(id="verse", name="主歌", start_bar=1, bars=2, energy=0.5),
            SectionSpec(id="chorus", name="副歌", start_bar=3, bars=2, energy=0.9),
        ],
        harmony=[
            HarmonySectionSpec(section="verse", progression=["C", "G"]),
            HarmonySectionSpec(section="chorus", progression=["Am", "F"]),
        ],
        tracks=[
            TrackSpec(
                id="bass",
                role="bass",
                instrument="electric_bass_finger",
                velocity=90,
            )
        ],
    )


def make_note(index: int, *, start: int | None = None) -> MidiEditorNote:
    return MidiEditorNote(
        id=f"b{index}",
        pitch=36 + index % 24,
        start_tick=index * 30 if start is None else start,
        duration_tick=120,
        velocity=70 + index % 40,
        channel=2,
    )


def make_document(notes: list[MidiEditorNote] | None = None) -> MidiEditorDocument:
    return MidiEditorDocument(
        song_id="song-a",
        version_id="v5",
        ppq=480,
        bpm=120,
        time_signature=(4, 4),
        total_bars=4,
        tracks=[
            MidiEditorTrack(
                id="bass",
                role="client-spoofed-role",
                name="Bass",
                channel=2,
                instrument="client-spoofed-instrument",
                notes=notes or [make_note(1, start=0)],
            )
        ],
    )


def make_request(scope: dict, notes: list[MidiEditorNote]) -> GenerateAiMidiEditProposalRequest:
    return GenerateAiMidiEditProposalRequest(
        instruction="  make it tighter  ",
        base_version_id="v5",
        editor_session_id=SESSION_ID,
        draft_revision=17,
        scope_revision=3,
        scope=scope,
        draft_notes=notes,
    )


def test_context_uses_authoritative_music_fields_and_scoped_draft_notes():
    note = make_note(1, start=3840)
    request = make_request(
        {
            "type": "section",
            "track_id": "bass",
            "section_id": "chorus",
            "start_tick": 3840,
            "end_tick": 7680,
        },
        [note],
    )
    context = build_ai_midi_edit_context(
        song_id="song-a",
        current_version_id="v5",
        request=request,
        music_spec=make_spec(),
        document=make_document(),
    )
    assert context.track_role == "bass"
    assert context.instrument == "electric_bass_finger"
    assert context.ppq == 480
    assert context.time_signature == (4, 4)
    assert context.key == "C"
    assert context.mode == "major"
    assert context.scale == "c-major"
    assert context.section and context.section.id == "chorus"
    assert [chord.symbol for chord in context.chords] == ["Am", "F"]
    assert context.scoped_notes[0].id == note.id
    assert context.draft_revision == 17
    assert context.scope_revision == 3


def test_context_rejects_project_version_track_and_section_boundary_mismatch():
    request = make_request({"type": "track", "track_id": "bass"}, [make_note(1)])
    with pytest.raises(AiMidiEditContextError, match="song_id"):
        build_ai_midi_edit_context(
            song_id="song-b",
            current_version_id="v5",
            request=request,
            music_spec=make_spec(),
            document=make_document(),
        )
    with pytest.raises(AiMidiEditContextError, match="过期"):
        current_document = make_document().model_copy(update={"version_id": "v6"})
        build_ai_midi_edit_context(
            song_id="song-a",
            current_version_id="v6",
            request=request,
            music_spec=make_spec(),
            document=current_document,
        )
    unknown = make_request({"type": "track", "track_id": "drums"}, [])
    with pytest.raises(AiMidiEditContextError, match="track_id"):
        build_ai_midi_edit_context(
            song_id="song-a",
            current_version_id="v5",
            request=unknown,
            music_spec=make_spec(),
            document=make_document(),
        )
    bad_section = make_request(
        {
            "type": "section",
            "track_id": "bass",
            "section_id": "chorus",
            "start_tick": 4000,
            "end_tick": 7680,
        },
        [],
    )
    with pytest.raises(MidiEditScopeError, match="边界"):
        build_ai_midi_edit_context(
            song_id="song-a",
            current_version_id="v5",
            request=bad_section,
            music_spec=make_spec(),
            document=make_document(),
        )


def test_request_rejects_blank_instruction_and_more_than_3000_notes():
    with pytest.raises(ValueError):
        make_request({"type": "track", "track_id": "bass"}, [make_note(i) for i in range(3001)])
    with pytest.raises(ValueError):
        GenerateAiMidiEditProposalRequest(
            instruction="   ",
            base_version_id="v5",
            editor_session_id=SESSION_ID,
            draft_revision=0,
            scope_revision=0,
            scope={"type": "track", "track_id": "bass"},
            draft_notes=[],
        )


def test_planner_payload_sends_exact_notes_up_to_128_and_omits_original_prompt():
    notes = [make_note(index) for index in range(MAX_EXACT_PLANNER_NOTES)]
    request = make_request({"type": "track", "track_id": "bass"}, notes)
    context = build_ai_midi_edit_context(
        song_id="song-a",
        current_version_id="v5",
        request=request,
        music_spec=make_spec(),
        document=make_document(notes),
    )
    payload = build_planner_payload(context, instruction=request.instruction)
    assert payload["notes"]["complete"] is True
    assert len(payload["notes"]["items"]) == MAX_EXACT_PLANNER_NOTES
    assert "secret original prompt" not in json.dumps(payload)
    assert payload["scope"] == {"type": "track", "noteCount": MAX_EXACT_PLANNER_NOTES}
    encoded = json.dumps(payload)
    assert "song-a" not in encoded
    assert '"v5"' not in encoded
    assert str(SESSION_ID) not in encoded
    assert '"id"' not in encoded


def test_planner_payload_compacts_3000_notes_to_deterministic_128_sample():
    notes = [make_note(index) for index in range(3000)]
    request = make_request({"type": "track", "track_id": "bass"}, notes)
    context = build_ai_midi_edit_context(
        song_id="song-a",
        current_version_id="v5",
        request=request,
        music_spec=make_spec(),
        document=make_document(notes),
    )
    first = build_planner_payload(context, instruction=request.instruction)
    second = build_planner_payload(context, instruction=request.instruction)
    assert first == second
    assert first["notes"]["complete"] is False
    assert first["notes"]["statistics"]["count"] == 3000
    assert len(first["notes"]["items"]) == 128
    assert len(json.dumps(first, ensure_ascii=False).encode("utf-8")) < 64 * 1024
