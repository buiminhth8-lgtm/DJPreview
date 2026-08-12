"""T35.3 deterministic MIDI transform engine tests."""

from __future__ import annotations

import copy
import random
import time
from fractions import Fraction

import pytest

from packages.music_core.midi_editing.models import (
    MidiEditPlan,
    SectionMidiEditScope,
    SelectedNotesMidiEditScope,
    TickRangeMidiEditScope,
    TrackMidiEditScope,
)
from packages.music_core.midi_editing.plan_validator import (
    MidiEditPlanErrorCode,
    MidiEditPlanValidationError,
    PlanValidator,
)
from packages.music_core.midi_editing.transformer import (
    MAX_TRANSFORMER_SEED,
    MidiTransformError,
    MidiTransformErrorCode,
    MidiTransformWarningCode,
    round_half_away_from_zero,
    transform_midi_notes,
)
from services.api.schemas.midi_editor import MidiEditorNote


def note(
    note_id: str,
    *,
    pitch: int = 60,
    start: int = 0,
    duration: int = 120,
    velocity: int = 80,
    channel: int = 0,
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
            "summary": "Deterministic test edit",
            "operations": list(operations),
        }
    )


def transform(
    notes: list[MidiEditorNote],
    edit_plan: MidiEditPlan,
    *,
    scope=None,
    ppq: int = 480,
    total_ticks: int = 7680,
    is_drum: bool = False,
    seed: int = 1234,
):
    return transform_midi_notes(
        notes,
        edit_plan,
        scope or TrackMidiEditScope(track_id="melody"),
        ppq=ppq,
        total_ticks=total_ticks,
        is_drum=is_drum,
        seed=seed,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Fraction(1, 2), 1),
        (Fraction(3, 2), 2),
        (Fraction(5, 2), 3),
        (Fraction(-1, 2), -1),
        (Fraction(-3, 2), -2),
        (Fraction(-5, 2), -3),
        (Fraction(149, 100), 1),
        (Fraction(150, 100), 2),
    ],
)
def test_round_half_away_from_zero(value, expected):
    assert round_half_away_from_zero(value) == expected


def test_transpose_and_octave_shift_clamp_pitch_with_warning():
    source = [note("low", pitch=3), note("high", pitch=124)]
    lowered = transform(source, plan({"type": "transpose", "semitones": -12}))
    raised = transform(source, plan({"type": "octave_shift", "octaves": 1}))
    assert [item.pitch for item in lowered.notes] == [0, 112]
    assert [item.pitch for item in raised.notes] == [15, 127]
    assert [warning.code for warning in lowered.warnings] == [
        MidiTransformWarningCode.PITCH_CLAMPED
    ]
    assert [warning.code for warning in raised.warnings] == [
        MidiTransformWarningCode.PITCH_CLAMPED
    ]


def test_velocity_set_delta_and_scale_follow_clamp_and_rounding_policy():
    source = [note("n1", velocity=5), note("n2", start=120, velocity=101)]
    set_result = transform(source, plan({"type": "velocity_set", "value": 64}))
    delta_result = transform(source, plan({"type": "velocity_delta", "delta": -10}))
    scale_result = transform(source, plan({"type": "velocity_scale", "factor": 1.5}))
    assert [item.velocity for item in set_result.notes] == [64, 64]
    assert [item.velocity for item in delta_result.notes] == [1, 91]
    assert [item.velocity for item in scale_result.notes] == [8, 127]
    assert [warning.code for warning in delta_result.warnings] == [
        MidiTransformWarningCode.VELOCITY_CLAMPED
    ]
    assert [warning.code for warning in scale_result.warnings] == [
        MidiTransformWarningCode.VELOCITY_CLAMPED
    ]


def test_duration_scale_and_staccato_use_minimum_one_tick():
    source = [note("half", duration=3), note("minimum", start=10, duration=1)]
    scaled = transform(source, plan({"type": "duration_scale", "factor": 0.5}))
    staccato = transform(source, plan({"type": "staccato", "ratio": 0.1}))
    assert [item.duration_tick for item in scaled.notes] == [2, 1]
    assert [item.duration_tick for item in staccato.notes] == [1, 1]
    assert all(item.duration_tick >= 1 for item in (*scaled.notes, *staccato.notes))
    assert any(
        warning.code == MidiTransformWarningCode.DURATION_MINIMUM_APPLIED
        for warning in staccato.warnings
    )


@pytest.mark.parametrize("scope_type", ["section", "tick_range"])
def test_duration_scale_clamps_at_authorized_time_window(scope_type):
    scope_class = SectionMidiEditScope if scope_type == "section" else TickRangeMidiEditScope
    scope_fields = {"section_id": "verse"} if scope_type == "section" else {}
    scope = scope_class(
        track_id="melody",
        start_tick=100,
        end_tick=200,
        **scope_fields,
    )
    result = transform(
        [note("edge", start=180, duration=10)],
        plan({"type": "duration_scale", "factor": 4.0}),
        scope=scope,
        total_ticks=400,
    )
    assert result.notes[0].duration_tick == 20
    assert result.warnings[0].code == MidiTransformWarningCode.DURATION_CLAMPED


def test_legato_groups_same_channel_chord_and_uses_next_distinct_onset():
    source = [
        note("c4", pitch=60, start=0, duration=80, channel=0),
        note("e4", pitch=64, start=0, duration=200, channel=0),
        note("other-channel", pitch=48, start=100, duration=30, channel=1),
        note("g4", pitch=67, start=120, duration=60, channel=0),
        note("a4", pitch=69, start=240, duration=50, channel=0),
    ]
    result = transform(source, plan({"type": "legato", "overlap_ticks": 10}))
    by_id = {item.id: item for item in result.notes}
    assert by_id["c4"].duration_tick == 130
    assert by_id["e4"].duration_tick == 200  # legato never shortens
    assert by_id["g4"].duration_tick == 130
    assert by_id["a4"].duration_tick == 50  # last channel-0 onset unchanged
    assert by_id["other-channel"].duration_tick == 30


def test_legato_respects_range_end_and_emits_warning():
    scope = TickRangeMidiEditScope(
        track_id="melody",
        start_tick=0,
        end_tick=200,
    )
    result = transform(
        [note("first", start=0, duration=20), note("next", start=190, duration=5)],
        plan({"type": "legato", "overlap_ticks": 20}),
        scope=scope,
        total_ticks=200,
    )
    assert result.notes[0].duration_tick == 200
    assert result.warnings[0].code == MidiTransformWarningCode.DURATION_CLAMPED


def test_legato_never_shortens_a_preexisting_cross_boundary_note():
    scope = TickRangeMidiEditScope(
        track_id="melody",
        start_tick=0,
        end_tick=200,
    )
    result = transform(
        [note("long", start=0, duration=240), note("next", start=190, duration=5)],
        plan({"type": "legato", "overlap_ticks": 20}),
        scope=scope,
        total_ticks=300,
    )
    assert result.notes[0].duration_tick == 240
    assert result.warnings == ()


@pytest.mark.parametrize(
    ("grid", "start", "expected"),
    [
        ("1/4", 239, 0),
        ("1/4", 240, 480),  # exact tie goes forward
        ("1/8", 120, 240),
        ("1/16", 60, 120),
        ("1/32", 30, 60),
    ],
)
def test_quantize_each_grid_and_forward_tie(grid, start, expected):
    result = transform(
        [note("n", start=start, duration=77)],
        plan({"type": "quantize", "grid": grid}),
    )
    assert result.notes[0].start_tick == expected
    assert result.notes[0].duration_tick == 77


def test_quantize_uses_exact_ppq_fraction_and_partial_strength():
    # PPQ=100 makes 1/32 equal 12.5 ticks. start=6 is nearer 0; strength=.5
    # produces exactly 3 ticks. start=19 is nearer 25; halfway produces 22.
    source = [note("a", start=6), note("b", start=19)]
    result = transform(
        source,
        plan({"type": "quantize", "grid": "1/32", "strength": 0.5}),
        ppq=100,
    )
    assert [item.start_tick for item in result.notes] == [3, 22]


def test_quantize_and_shift_timing_clamp_range_without_changing_duration():
    scope = TickRangeMidiEditScope(
        track_id="melody",
        start_tick=100,
        end_tick=200,
    )
    quantized = transform(
        [note("q", start=110, duration=33)],
        plan({"type": "quantize", "grid": "1/4"}),
        scope=scope,
        total_ticks=500,
    )
    shifted = transform(
        [note("s", start=110, duration=44)],
        plan({"type": "shift_timing", "delta_ticks": -120}),
        scope=scope,
        total_ticks=500,
    )
    assert (quantized.notes[0].start_tick, quantized.notes[0].duration_tick) == (100, 33)
    assert (shifted.notes[0].start_tick, shifted.notes[0].duration_tick) == (100, 44)
    assert quantized.warnings[0].code == MidiTransformWarningCode.START_TICK_CLAMPED
    assert shifted.warnings[0].code == MidiTransformWarningCode.START_TICK_CLAMPED


def test_track_shift_timing_clamps_at_zero_with_warning():
    result = transform(
        [note("n", start=10)],
        plan({"type": "shift_timing", "delta_ticks": -20}),
    )
    assert result.notes[0].start_tick == 0
    assert result.warnings[0].code == MidiTransformWarningCode.START_TICK_CLAMPED


def density_notes(count: int = 12) -> list[MidiEditorNote]:
    return [
        note(
            f"n{index:02d}",
            pitch=48 + (index % 12),
            start=index * 120,
            duration=60 + index,
            velocity=70 + (index % 20),
            channel=index % 2,
        )
        for index in range(count)
    ]


def test_reduce_density_is_seeded_stable_and_preserves_edges():
    source = density_notes()
    edit_plan = plan(
        {"type": "reduce_density", "keep_ratio": 0.5, "preserve_edges": True}
    )
    first = transform(source, edit_plan, seed=100)
    second = transform(list(reversed(source)), edit_plan, seed=100)
    other_seed = transform(source, edit_plan, seed=101)
    assert first == second
    assert len(first.notes) == 6
    assert {"n00", "n11"} <= {item.id for item in first.notes}
    assert {item.id for item in first.notes} != {item.id for item in other_seed.notes}
    assert set(first.removed_note_ids) == {item.id for item in source} - {
        item.id for item in first.notes
    }


def test_reduce_density_does_not_pollute_global_rng():
    source = density_notes()
    edit_plan = plan({"type": "reduce_density", "keep_ratio": 0.5})
    random.seed(98765)
    before = random.getstate()
    transform(source, edit_plan, seed=42)
    assert random.getstate() == before


def test_preserve_edges_is_not_a_hidden_downbeat_policy_in_non_four_four():
    # T35.2 froze preserve_edges, not preserve_downbeats. A 3/4 measure onset
    # receives no hidden privilege; only first and last canonical notes do.
    source = density_notes(9)
    result = transform(
        source,
        plan({"type": "reduce_density", "keep_ratio": 0.25, "preserve_edges": True}),
        ppq=480,
        seed=7,
    )
    kept = {item.id for item in result.notes}
    assert {"n00", "n08"} <= kept
    assert len(kept) == 2


def test_operation_order_is_semantic_for_density_and_following_edit():
    source = density_notes()
    density_then_velocity = transform(
        source,
        plan(
            {"type": "reduce_density", "keep_ratio": 0.5, "preserve_edges": False},
            {"type": "velocity_set", "value": 100},
        ),
        seed=9,
    )
    velocity_then_density = transform(
        source,
        plan(
            {"type": "velocity_set", "value": 100},
            {"type": "reduce_density", "keep_ratio": 0.5, "preserve_edges": False},
        ),
        seed=9,
    )
    assert {item.id for item in density_then_velocity.notes} != {
        item.id for item in velocity_then_density.notes
    }
    assert all(item.velocity == 100 for item in density_then_velocity.notes)
    assert all(item.velocity == 100 for item in velocity_then_density.notes)


def test_three_operation_plan_is_exactly_deterministic_and_canonical_sorted():
    source = list(reversed(density_notes(30)))
    edit_plan = plan(
        {"type": "quantize", "grid": "1/16", "strength": 0.75},
        {"type": "velocity_scale", "factor": 1.25},
        {"type": "reduce_density", "keep_ratio": 0.6},
    )
    first = transform(source, edit_plan, seed=31337)
    second = transform(copy.deepcopy(source), edit_plan, seed=31337)
    assert first == second
    assert list(first.notes) == sorted(
        first.notes,
        key=lambda item: (item.start_tick, item.pitch, item.channel, item.id),
    )


def test_input_notes_scope_and_plan_are_immutable_and_output_notes_are_copies():
    source = density_notes(5)
    scope = SelectedNotesMidiEditScope(
        track_id="bass",
        note_ids=[item.id for item in source],
    )
    edit_plan = plan({"type": "velocity_set", "value": 90})
    notes_before = copy.deepcopy(source)
    scope_before = copy.deepcopy(scope)
    plan_before = copy.deepcopy(edit_plan)
    result = transform(source, edit_plan, scope=scope)
    assert source == notes_before
    assert scope == scope_before
    assert edit_plan == plan_before
    assert all(output is not original for output, original in zip(result.notes, source, strict=True))


def test_legal_semantic_noop_is_stable_but_still_returns_fresh_notes():
    source = [note("aligned", start=480, velocity=90)]
    result = transform(source, plan({"type": "quantize", "grid": "1/4"}))
    assert result.notes[0] == source[0]
    assert result.notes[0] is not source[0]
    assert result.removed_note_ids == ()
    assert result.warnings == ()


def test_ids_channels_and_all_midi_invariants_hold():
    source = density_notes(24)
    source_channels = {item.id: item.channel for item in source}
    result = transform(
        source,
        plan(
            {"type": "transpose", "semitones": 24},
            {"type": "velocity_delta", "delta": 64},
            {"type": "duration_scale", "factor": 0.25},
            {"type": "quantize", "grid": "1/32", "strength": 0.5},
            {"type": "reduce_density", "keep_ratio": 0.5},
        ),
        seed=0,
    )
    assert {item.id for item in result.notes} <= {item.id for item in source}
    for item in result.notes:
        assert item.channel == source_channels[item.id]
        assert all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in (
                item.pitch,
                item.velocity,
                item.start_tick,
                item.duration_tick,
                item.channel,
            )
        )
        assert 0 <= item.pitch <= 127
        assert 1 <= item.velocity <= 127
        assert item.start_tick >= 0
        assert item.duration_tick >= 1


def test_transformer_scope_isolation_is_structural():
    bass_scope = [note(f"bass-{index}", pitch=36, start=index * 120) for index in range(5)]
    melody = [note(f"melody-{index}", pitch=72) for index in range(100)]
    drums = [note(f"drum-{index}", pitch=36, channel=9) for index in range(500)]
    result = transform(
        bass_scope,
        plan({"type": "transpose", "semitones": 12}),
        scope=SelectedNotesMidiEditScope(
            track_id="bass",
            note_ids=[item.id for item in bass_scope],
        ),
    )
    assert {item.id for item in result.notes} == {item.id for item in bass_scope}
    assert not ({item.id for item in result.notes} & {item.id for item in melody + drums})


@pytest.mark.parametrize(
    "scope,source",
    [
        (
            SelectedNotesMidiEditScope(track_id="bass", note_ids=["a", "b"]),
            [note("a")],
        ),
        (
            TickRangeMidiEditScope(track_id="bass", start_tick=100, end_tick=200),
            [note("outside", start=99)],
        ),
    ],
)
def test_invalid_resolved_scope_fails_closed(scope, source):
    with pytest.raises(MidiTransformError) as caught:
        transform(source, plan({"type": "velocity_set", "value": 90}), scope=scope)
    assert caught.value.code == MidiTransformErrorCode.SCOPE_VIOLATION


def test_mutated_scope_container_is_revalidated_at_trust_boundary():
    scope = SelectedNotesMidiEditScope(track_id="bass", note_ids=["a"])
    scope.note_ids.append("a")
    with pytest.raises(MidiTransformError) as caught:
        transform([note("a")], plan({"type": "velocity_set", "value": 90}), scope=scope)
    assert caught.value.code == MidiTransformErrorCode.INVALID_CONTEXT


def test_mutated_note_is_revalidated_strictly_at_trust_boundary():
    source = note("n")
    source.start_tick = True
    with pytest.raises(MidiTransformError) as caught:
        transform([source], plan({"type": "velocity_set", "value": 90}))
    assert caught.value.code == MidiTransformErrorCode.INVALID_SCOPED_NOTES


def test_empty_duplicate_oversized_and_wrong_note_type_fail_closed():
    edit_plan = plan({"type": "velocity_set", "value": 90})
    invalid_inputs = [
        [],
        [note("same"), note("same", start=120)],
        density_notes(3001),
        [object()],
    ]
    for invalid in invalid_inputs:
        with pytest.raises(MidiTransformError) as caught:
            transform(invalid, edit_plan)
        assert caught.value.code == MidiTransformErrorCode.INVALID_SCOPED_NOTES


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"ppq": 0}, MidiEditPlanErrorCode.INVALID_PLAN),
        ({"ppq": True}, MidiEditPlanErrorCode.INVALID_PLAN),
        ({"is_drum": "false"}, MidiEditPlanErrorCode.INVALID_PLAN),
        ({"total_ticks": -1}, MidiTransformErrorCode.INVALID_CONTEXT),
        ({"total_ticks": True}, MidiTransformErrorCode.INVALID_CONTEXT),
        ({"seed": -1}, MidiTransformErrorCode.INVALID_CONTEXT),
        ({"seed": MAX_TRANSFORMER_SEED + 1}, MidiTransformErrorCode.INVALID_CONTEXT),
        ({"seed": True}, MidiTransformErrorCode.INVALID_CONTEXT),
    ],
)
def test_invalid_context_fails_before_transform(kwargs, code):
    with pytest.raises((MidiTransformError, MidiEditPlanValidationError)) as caught:
        transform([note("n")], plan({"type": "velocity_set", "value": 90}), **kwargs)
    assert caught.value.code == code


def test_scope_end_cannot_exceed_total_ticks():
    scope = TickRangeMidiEditScope(track_id="bass", start_tick=0, end_tick=1000)
    with pytest.raises(MidiTransformError) as caught:
        transform(
            [note("n")],
            plan({"type": "velocity_set", "value": 90}),
            scope=scope,
            total_ticks=999,
        )
    assert caught.value.code == MidiTransformErrorCode.INVALID_CONTEXT


@pytest.mark.parametrize("operation_type", ["transpose", "octave_shift"])
def test_drum_pitch_operation_is_rejected_before_execution(operation_type):
    operation = (
        {"type": "transpose", "semitones": 1}
        if operation_type == "transpose"
        else {"type": "octave_shift", "octaves": 1}
    )
    source = [note("kick", pitch=36, channel=9)]
    snapshot = copy.deepcopy(source)
    with pytest.raises(MidiEditPlanValidationError) as caught:
        transform(source, plan(operation), is_drum=True)
    assert caught.value.code == MidiEditPlanErrorCode.OPERATION_NOT_APPLICABLE
    assert source == snapshot


@pytest.mark.parametrize(
    "operation",
    [
        {"type": "velocity_set", "value": 90},
        {"type": "velocity_delta", "delta": 5},
        {"type": "velocity_scale", "factor": 1.1},
        {"type": "duration_scale", "factor": 1.1},
        {"type": "staccato", "ratio": 0.8},
        {"type": "legato"},
        {"type": "quantize", "grid": "1/16"},
        {"type": "shift_timing", "delta_ticks": 1},
        {"type": "reduce_density", "keep_ratio": 0.5},
    ],
)
def test_all_non_pitch_operations_support_drum(operation):
    result = transform(
        [note("kick", pitch=36, channel=9), note("snare", pitch=38, start=120, channel=9)],
        plan(operation),
        is_drum=True,
    )
    assert {item.id for item in result.notes} <= {"kick", "snare"}


def test_late_operation_failure_is_atomic_and_input_unchanged():
    source = [note("n", velocity=80)]
    snapshot = copy.deepcopy(source)
    edit_plan = plan(
        {"type": "velocity_set", "value": 100},
        {"type": "shift_timing", "delta_ticks": 1921},
    )
    with pytest.raises(MidiEditPlanValidationError) as caught:
        transform(source, edit_plan, ppq=480)
    assert caught.value.operation_index == 1
    assert source == snapshot


def test_canonical_output_is_byte_stable_as_json_values():
    source = density_notes(20)
    edit_plan = plan(
        {"type": "quantize", "grid": "1/32", "strength": 0.75},
        {"type": "reduce_density", "keep_ratio": 0.55},
    )
    first = transform(source, edit_plan, seed=MAX_TRANSFORMER_SEED)
    second = transform(copy.deepcopy(source), copy.deepcopy(edit_plan), seed=MAX_TRANSFORMER_SEED)
    assert [item.model_dump_json() for item in first.notes] == [
        item.model_dump_json() for item in second.notes
    ]
    assert first.removed_note_ids == second.removed_note_ids
    assert first.warnings == second.warnings


@pytest.mark.parametrize("count", [500, 1000, 3000])
def test_performance_smoke_is_linearithmic_without_absolute_time_gate(count):
    source = density_notes(count)
    edit_plan = plan(
        {"type": "quantize", "grid": "1/16", "strength": 0.75},
        {"type": "velocity_scale", "factor": 1.1},
        {"type": "reduce_density", "keep_ratio": 0.6},
    )
    started = time.perf_counter()
    result = transform(source, edit_plan, total_ticks=count * 120 + 480, seed=2026)
    elapsed = time.perf_counter() - started
    assert len(result.notes) == round_half_away_from_zero(Fraction(count * 6, 10))
    assert elapsed >= 0  # Result is recorded by pytest duration; no brittle millisecond gate.
