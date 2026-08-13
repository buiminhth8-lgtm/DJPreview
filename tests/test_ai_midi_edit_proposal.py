"""T35.4 stateless AI MIDI edit Proposal and fail-closed Diff tests."""

from __future__ import annotations

import copy
import time
from datetime import datetime, timezone
from fractions import Fraction
from uuid import UUID

import pytest
from pydantic import ValidationError

from packages.music_core.midi_editing.diff import (
    MidiNoteDiffError,
    MidiNoteDiffErrorCode,
    calculate_midi_note_diff,
)
from packages.music_core.midi_editing.models import (
    MidiEditPlan,
    SelectedNotesMidiEditScope,
    TrackMidiEditScope,
)
from packages.music_core.midi_editing.plan_validator import PlanValidator
from packages.music_core.midi_editing.scope import scope_fingerprint
from packages.music_core.midi_editing.transformer import (
    MidiTransformResult,
    MidiTransformWarning,
    MidiTransformWarningCode,
    round_half_away_from_zero,
)
from services.api.schemas.ai_midi_edit import (
    AiMidiEditContext,
    AiMidiEditProposal,
    MidiNoteModification,
)
from services.api.schemas.midi_editor import MidiEditorNote
from services.api.services import ai_midi_edit_service
from services.api.services.ai_midi_edit_service import (
    AiMidiEditProposalError,
    AiMidiEditProposalErrorCode,
    build_midi_edit_proposal,
)

SESSION_ID = UUID("8d2cf52d-c4d4-4f5a-87e7-1b5860c7a663")
PROPOSAL_ID = UUID("efc570c5-bf7e-44f2-a553-bb65c8316c02")
CREATED_AT = datetime(2026, 8, 13, 2, 30, tzinfo=timezone.utc)


def note(
    note_id: str,
    *,
    pitch: int = 60,
    start: int = 0,
    duration: int = 120,
    velocity: int = 80,
    channel: int = 2,
) -> MidiEditorNote:
    return MidiEditorNote(
        id=note_id,
        pitch=pitch,
        start_tick=start,
        duration_tick=duration,
        velocity=velocity,
        channel=channel,
    )


def plan(*operations: dict[str, object]) -> MidiEditPlan:
    return PlanValidator.parse(
        {
            "schema_version": "1.0",
            "summary": "Fixture plan",
            "operations": list(operations),
        }
    )


def context(
    notes: list[MidiEditorNote],
    *,
    draft_revision: int = 12,
    scope_revision: int = 4,
    selected: bool = False,
) -> AiMidiEditContext:
    scope = (
        SelectedNotesMidiEditScope(
            track_id="bass",
            note_ids=[item.id for item in notes],
        )
        if selected
        else TrackMidiEditScope(track_id="bass")
    )
    return AiMidiEditContext(
        song_id="song-fixture",
        base_version_id="v7",
        editor_session_id=SESSION_ID,
        draft_revision=draft_revision,
        scope_revision=scope_revision,
        scope_fingerprint=scope_fingerprint(scope),
        scope=scope,
        track_id="bass",
        track_role="bass",
        instrument="electric_bass_finger",
        is_drum=False,
        channel_summary=[2],
        ppq=480,
        tempo_bpm=120,
        time_signature=(4, 4),
        total_ticks=max(7680, max((item.start_tick for item in notes), default=0) + 480),
        scoped_notes=notes,
        key="C",
        mode="major",
        scale="c-major",
    )


def build(
    edit_context: AiMidiEditContext,
    edit_plan: MidiEditPlan,
    *,
    seed: int = 1234,
) -> AiMidiEditProposal:
    return build_midi_edit_proposal(
        edit_context,
        edit_plan,
        seed,
        planner_provider="fixture",
        planner_model=None,
        prompt_version="fixture-v1",
        proposal_id=PROPOSAL_ID,
        created_at=CREATED_AT,
    )


def semantic_dump(proposal: AiMidiEditProposal) -> dict[str, object]:
    value = proposal.model_dump(mode="json")
    value.pop("proposal_id")
    value.pop("created_at")
    return value


def density_notes(count: int) -> list[MidiEditorNote]:
    return [
        note(
            f"n{index:04d}",
            pitch=36 + (index % 24),
            start=index * 60,
            duration=45 + (index % 30),
            velocity=60 + (index % 50),
        )
        for index in range(count)
    ]


def test_diff_classifies_modified_deleted_and_excludes_unchanged():
    before = [note("same"), note("changed", start=120), note("deleted", start=240)]
    after = [
        note("same"),
        note("changed", pitch=64, start=130, duration=180, velocity=99),
    ]
    diff = calculate_midi_note_diff(
        before,
        after,
        authorized_note_ids=[item.id for item in before],
    )
    assert diff.added == ()
    assert [item.id for item in diff.deleted] == ["deleted"]
    assert [item.note_id for item in diff.modified] == ["changed"]
    assert diff.modified[0].changed_fields == (
        "pitch",
        "start_tick",
        "duration_tick",
        "velocity",
    )
    assert diff.change_count == 2
    assert diff.is_noop is False


def test_diff_is_stably_sorted_by_t35_canonical_note_order():
    before = [
        note("late", pitch=40, start=200),
        note("high", pitch=72, start=100),
        note("low", pitch=48, start=100),
    ]
    after = [
        note("late", pitch=41, start=200),
        note("high", pitch=73, start=100),
        note("low", pitch=49, start=100),
    ]
    first = calculate_midi_note_diff(before, after, authorized_note_ids=["late", "high", "low"])
    second = calculate_midi_note_diff(
        list(reversed(before)),
        list(reversed(after)),
        authorized_note_ids=["low", "high", "late"],
    )
    assert [item.id for item in first.before_notes] == ["low", "high", "late"]
    assert [item.note_id for item in first.modified] == ["low", "high", "late"]
    assert first == second


def test_diff_noop_returns_empty_change_sets_and_fresh_snapshots():
    source = [note("a"), note("b", start=120)]
    diff = calculate_midi_note_diff(source, copy.deepcopy(source), authorized_note_ids=["a", "b"])
    assert diff.added == diff.deleted == diff.modified == ()
    assert diff.change_count == 0
    assert diff.is_noop is True
    assert diff.before_notes[0] is not source[0]


@pytest.mark.parametrize("side", ["before", "after"])
def test_diff_rejects_duplicate_note_ids(side):
    before = [note("a")]
    after = [note("a")]
    duplicate = [note("a"), note("a", start=120)]
    if side == "before":
        before = duplicate
    else:
        after = duplicate
    with pytest.raises(MidiNoteDiffError) as caught:
        calculate_midi_note_diff(before, after, authorized_note_ids=["a"])
    assert caught.value.code == MidiNoteDiffErrorCode.DUPLICATE_NOTE_ID


def test_diff_rejects_unknown_after_id_instead_of_accepting_added():
    with pytest.raises(MidiNoteDiffError) as caught:
        calculate_midi_note_diff(
            [note("a")],
            [note("a"), note("new", start=120)],
            authorized_note_ids=["a", "new"],
        )
    assert caught.value.code == MidiNoteDiffErrorCode.UNKNOWN_AFTER_ID
    assert caught.value.note_id == "new"


@pytest.mark.parametrize("side", ["before", "after"])
def test_diff_rejects_scope_outside_ids(side):
    before = [note("authorized")]
    after = [note("authorized", velocity=90)]
    if side == "before":
        before.append(note("foreign", start=120))
    else:
        after.append(note("foreign", start=120))
    with pytest.raises(MidiNoteDiffError) as caught:
        calculate_midi_note_diff(before, after, authorized_note_ids=["authorized"])
    assert caught.value.code == MidiNoteDiffErrorCode.SCOPE_VIOLATION


def test_diff_rejects_channel_change_as_invariant_violation():
    with pytest.raises(MidiNoteDiffError) as caught:
        calculate_midi_note_diff(
            [note("a", channel=2)],
            [note("a", channel=3)],
            authorized_note_ids=["a"],
        )
    assert caught.value.code == MidiNoteDiffErrorCode.CHANNEL_CHANGED


def test_modified_note_transport_schema_requires_exact_changed_fields():
    before = note("a", pitch=60)
    after = note("a", pitch=61)
    with pytest.raises(ValidationError):
        MidiNoteModification(
            note_id="a",
            before=before,
            after=after,
            changed_fields=("velocity",),
        )


def test_builder_captures_all_frozen_snapshot_identity_fields():
    edit_context = context([note("a")], draft_revision=12, scope_revision=5, selected=True)
    proposal = build(edit_context, plan({"type": "transpose", "semitones": 2}), seed=99)
    assert proposal.proposal_id == PROPOSAL_ID
    assert proposal.song_id == "song-fixture"
    assert proposal.base_version_id == "v7"
    assert proposal.editor_session_id == SESSION_ID
    assert proposal.base_draft_revision == 12
    assert proposal.base_scope_revision == 5
    assert proposal.scope_fingerprint == edit_context.scope_fingerprint
    assert proposal.track_id == "bass"
    assert proposal.track_role == "bass"
    assert proposal.scope == edit_context.scope
    assert proposal.transformer_seed == 99
    assert proposal.planner_provider == "fixture"
    assert proposal.prompt_version == "fixture-v1"
    assert proposal.created_at == CREATED_AT


def test_builder_transpose_quantize_velocity_combination_produces_exact_diff():
    source = [note("a", pitch=60, start=70, velocity=80), note("b", pitch=64, start=120, velocity=100)]
    proposal = build(
        context(source),
        plan(
            {"type": "transpose", "semitones": 2},
            {"type": "quantize", "grid": "1/16"},
            {"type": "velocity_set", "value": 90},
        ),
    )
    assert proposal.added == []
    assert proposal.deleted == []
    assert [item.note_id for item in proposal.modified] == ["a", "b"]
    assert proposal.modified[0].changed_fields == ("pitch", "start_tick", "velocity")
    assert proposal.modified[1].changed_fields == ("pitch", "velocity")
    assert proposal.change_count == 2
    assert proposal.is_noop is False
    assert [item.pitch for item in proposal.after_notes] == [62, 66]


def test_builder_density_deleted_diff_is_exact_and_added_remains_empty():
    source = density_notes(20)
    proposal = build(
        context(source),
        plan({"type": "reduce_density", "keep_ratio": 0.5, "preserve_edges": True}),
        seed=42,
    )
    assert len(proposal.after_notes) == 10
    assert len(proposal.deleted) == 10
    assert proposal.modified == []
    assert proposal.added == []
    assert proposal.change_count == 10
    assert {item.id for item in proposal.deleted} == {
        item.id for item in source
    } - {item.id for item in proposal.after_notes}


def test_builder_noop_is_successful_and_does_not_manufacture_diff():
    source = [note("aligned", start=480, velocity=90)]
    proposal = build(context(source), plan({"type": "quantize", "grid": "1/4"}))
    assert proposal.before_notes == proposal.after_notes
    assert proposal.added == proposal.deleted == proposal.modified == []
    assert proposal.change_count == 0
    assert proposal.is_noop is True
    assert proposal.warnings == []


def test_builder_maps_only_real_deterministic_transform_warnings():
    source = [note("high", pitch=127)]
    proposal = build(context(source), plan({"type": "transpose", "semitones": 12}))
    assert len(proposal.warnings) == 1
    assert proposal.warnings[0].code == MidiTransformWarningCode.PITCH_CLAMPED
    assert proposal.warnings[0].operation_index == 0
    assert proposal.warnings[0].note_id == "high"


def test_same_context_plan_seed_produces_same_semantic_proposal():
    source = density_notes(40)
    edit_context = context(source)
    edit_plan = plan(
        {"type": "quantize", "grid": "1/16", "strength": 0.75},
        {"type": "velocity_scale", "factor": 1.1},
        {"type": "reduce_density", "keep_ratio": 0.6},
    )
    first = build(edit_context, edit_plan, seed=31337)
    second = build_midi_edit_proposal(
        edit_context,
        edit_plan,
        31337,
        planner_provider="fixture",
        planner_model=None,
        prompt_version="fixture-v1",
        proposal_id=UUID("06b482b9-6c76-4c33-a3da-f9611eea9a3d"),
        created_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )
    assert first.proposal_id != second.proposal_id
    assert semantic_dump(first) == semantic_dump(second)


def test_default_proposal_id_is_unique_and_not_used_for_semantics():
    edit_context = context([note("a")])
    edit_plan = plan({"type": "velocity_set", "value": 90})
    kwargs = {
        "planner_provider": "fixture",
        "planner_model": None,
        "prompt_version": "fixture-v1",
    }
    first = build_midi_edit_proposal(edit_context, edit_plan, 1, **kwargs)
    second = build_midi_edit_proposal(edit_context, edit_plan, 1, **kwargs)
    assert first.proposal_id != second.proposal_id
    assert first.base_version_id == second.base_version_id
    assert first.base_draft_revision == second.base_draft_revision
    assert first.scope_fingerprint == second.scope_fingerprint


def test_snapshot_does_not_refresh_when_original_context_changes_later():
    edit_context = context([note("a")], draft_revision=12)
    proposal = build(edit_context, plan({"type": "velocity_set", "value": 90}))
    edit_context.draft_revision = 13
    edit_context.scoped_notes[0].velocity = 1
    assert proposal.base_draft_revision == 12
    assert proposal.before_notes[0].velocity == 80


def test_builder_does_not_mutate_context_plan_or_input_notes():
    source = density_notes(12)
    edit_context = context(source, selected=True)
    edit_plan = plan(
        {"type": "velocity_scale", "factor": 1.1},
        {"type": "reduce_density", "keep_ratio": 0.5},
    )
    source_before = copy.deepcopy(source)
    context_before = copy.deepcopy(edit_context)
    plan_before = copy.deepcopy(edit_plan)
    proposal = build(edit_context, edit_plan)
    assert source == source_before
    assert edit_context == context_before
    assert edit_plan == plan_before
    assert proposal.before_notes is not edit_context.scoped_notes
    assert all(
        result_note is not input_note
        for result_note, input_note in zip(proposal.before_notes, source, strict=True)
    )


def test_scope_isolation_is_structural_in_proposal_and_diff():
    bass = [note(f"bass-{index}", pitch=36, start=index * 120) for index in range(5)]
    melody_ids = {f"melody-{index}" for index in range(100)}
    drum_ids = {f"drum-{index}" for index in range(500)}
    proposal = build(
        context(bass, selected=True),
        plan({"type": "transpose", "semitones": 12}),
    )
    proposal_ids = {
        *(item.id for item in proposal.before_notes),
        *(item.id for item in proposal.after_notes),
        *(item.id for item in proposal.added),
        *(item.id for item in proposal.deleted),
        *(item.note_id for item in proposal.modified),
    }
    assert proposal_ids == {item.id for item in bass}
    assert not proposal_ids & (melody_ids | drum_ids)


@pytest.mark.parametrize("mismatch", ["track", "fingerprint"])
def test_builder_rejects_context_snapshot_identity_mismatch(mismatch):
    edit_context = context([note("a")])
    if mismatch == "track":
        edit_context.track_id = "melody"
    else:
        edit_context.scope_fingerprint = "0" * 64
    with pytest.raises(AiMidiEditProposalError) as caught:
        build(edit_context, plan({"type": "velocity_set", "value": 90}))
    assert caught.value.code == AiMidiEditProposalErrorCode.SNAPSHOT_IDENTITY_MISMATCH


def test_builder_revalidates_mutated_context_at_trust_boundary():
    edit_context = context([note("a")], selected=True)
    edit_context.scope.note_ids.append("a")
    with pytest.raises(AiMidiEditProposalError) as caught:
        build(edit_context, plan({"type": "velocity_set", "value": 90}))
    assert caught.value.code == AiMidiEditProposalErrorCode.INVALID_CONTEXT


def test_proposal_schema_rejects_wrong_change_count_and_noop_flags():
    proposal = build(context([note("a")]), plan({"type": "velocity_set", "value": 90}))
    value = proposal.model_dump(mode="python")
    value["change_count"] = 0
    value["is_noop"] = True
    with pytest.raises(ValidationError):
        AiMidiEditProposal.model_validate(value)


@pytest.mark.parametrize("tamper", ["fingerprint", "selected_membership"])
def test_proposal_schema_rejects_scope_snapshot_tampering(tamper):
    proposal = build(
        context([note("a"), note("b", start=120)], selected=True),
        plan({"type": "velocity_set", "value": 90}),
    )
    value = proposal.model_dump(mode="python")
    if tamper == "fingerprint":
        value["scope_fingerprint"] = "0" * 64
    else:
        value["scope"]["note_ids"].append("foreign")
        value["scope_fingerprint"] = scope_fingerprint(
            SelectedNotesMidiEditScope.model_validate(value["scope"])
        )
    with pytest.raises(ValidationError):
        AiMidiEditProposal.model_validate(value)


@pytest.mark.parametrize("tamper", ["deleted_value", "modified_value", "order", "warning"])
def test_proposal_schema_rejects_internally_inconsistent_transport(tamper):
    source = [note("a", pitch=126, start=0), note("b", start=120)]
    edit_plan = plan(
        {"type": "transpose", "semitones": 12},
        {"type": "reduce_density", "keep_ratio": 0.5, "preserve_edges": False},
    )
    proposal = build(context(source), edit_plan, seed=5)
    value = proposal.model_dump(mode="python")
    if tamper == "deleted_value":
        value["deleted"][0]["velocity"] = 1
    elif tamper == "modified_value":
        # Choose a deterministic Plan without density so a modified Note exists.
        proposal = build(context(source), plan({"type": "transpose", "semitones": 12}))
        value = proposal.model_dump(mode="python")
        value["modified"][0]["after"]["velocity"] = 1
        value["modified"][0]["changed_fields"] = ("pitch", "velocity")
    elif tamper == "order":
        value["before_notes"] = list(reversed(value["before_notes"]))
    else:
        value["warnings"][0]["operation_type"] = "velocity_set"
    with pytest.raises(ValidationError):
        AiMidiEditProposal.model_validate(value)


def test_proposal_schema_roundtrip_is_stable():
    proposal = build(
        context([note("a", pitch=127), note("b", start=120)]),
        plan({"type": "transpose", "semitones": 12}),
    )
    assert AiMidiEditProposal.model_validate_json(proposal.model_dump_json()) == proposal


def test_builder_rejects_transformer_unknown_after_id(monkeypatch):
    edit_context = context([note("a")])

    def invalid_transform(*args, **kwargs):
        return MidiTransformResult(
            notes=(note("a"), note("new", start=120)),
            removed_note_ids=(),
            seed=1234,
            warnings=(),
        )

    monkeypatch.setattr(ai_midi_edit_service, "transform_midi_notes", invalid_transform)
    with pytest.raises(MidiNoteDiffError) as caught:
        build(edit_context, plan({"type": "velocity_set", "value": 90}))
    assert caught.value.code == MidiNoteDiffErrorCode.SCOPE_VIOLATION


def test_builder_rejects_transformer_channel_change(monkeypatch):
    edit_context = context([note("a", channel=2)])

    def invalid_transform(*args, **kwargs):
        return MidiTransformResult(
            notes=(note("a", channel=3),),
            removed_note_ids=(),
            seed=1234,
            warnings=(),
        )

    monkeypatch.setattr(ai_midi_edit_service, "transform_midi_notes", invalid_transform)
    with pytest.raises(MidiNoteDiffError) as caught:
        build(edit_context, plan({"type": "velocity_set", "value": 90}))
    assert caught.value.code == MidiNoteDiffErrorCode.CHANNEL_CHANGED


def test_builder_rejects_removed_id_mismatch_without_partial_proposal(monkeypatch):
    edit_context = context([note("a"), note("b", start=120)])

    def inconsistent_transform(*args, **kwargs):
        return MidiTransformResult(
            notes=(note("a"),),
            removed_note_ids=(),
            seed=1234,
            warnings=(),
        )

    monkeypatch.setattr(ai_midi_edit_service, "transform_midi_notes", inconsistent_transform)
    with pytest.raises(AiMidiEditProposalError) as caught:
        build(edit_context, plan({"type": "velocity_set", "value": 90}))
    assert caught.value.code == AiMidiEditProposalErrorCode.RESULT_MISMATCH


def test_builder_rejects_transformer_seed_mismatch(monkeypatch):
    edit_context = context([note("a")])

    def inconsistent_transform(*args, **kwargs):
        return MidiTransformResult(
            notes=(note("a"),),
            removed_note_ids=(),
            seed=999,
            warnings=(),
        )

    monkeypatch.setattr(ai_midi_edit_service, "transform_midi_notes", inconsistent_transform)
    with pytest.raises(AiMidiEditProposalError) as caught:
        build(edit_context, plan({"type": "velocity_set", "value": 90}))
    assert caught.value.code == AiMidiEditProposalErrorCode.RESULT_MISMATCH


def test_builder_propagates_transformer_failure_without_partial_proposal(monkeypatch):
    edit_context = context([note("a")])

    def failed_transform(*args, **kwargs):
        raise RuntimeError("transform failed")

    monkeypatch.setattr(ai_midi_edit_service, "transform_midi_notes", failed_transform)
    with pytest.raises(RuntimeError, match="transform failed"):
        build(edit_context, plan({"type": "velocity_set", "value": 90}))


def test_builder_rejects_invalid_envelope_metadata_atomically():
    with pytest.raises(AiMidiEditProposalError) as caught:
        build_midi_edit_proposal(
            context([note("a")]),
            plan({"type": "velocity_set", "value": 90}),
            1,
            planner_provider="",
            planner_model=None,
            prompt_version="fixture-v1",
            created_at=CREATED_AT,
        )
    assert caught.value.code == AiMidiEditProposalErrorCode.INVALID_PROPOSAL_METADATA


@pytest.mark.parametrize("count", [500, 1000, 3000])
def test_proposal_and_diff_performance_smoke_without_absolute_gate(count):
    source = density_notes(count)
    edit_plan = plan(
        {"type": "quantize", "grid": "1/16", "strength": 0.75},
        {"type": "velocity_scale", "factor": 1.1},
        {"type": "reduce_density", "keep_ratio": 0.6},
    )
    started = time.perf_counter()
    proposal = build(context(source), edit_plan, seed=2026)
    elapsed = time.perf_counter() - started
    expected_after = round_half_away_from_zero(Fraction(count * 6, 10))
    assert len(proposal.after_notes) == expected_after
    assert proposal.change_count >= count - expected_after
    assert elapsed >= 0
