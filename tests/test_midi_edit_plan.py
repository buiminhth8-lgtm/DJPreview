"""T35.2 canonical MidiEditPlan schema and fail-closed validator tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from packages.music_core.midi_editing.models import (
    MidiEditPlan,
    MidiEditScope,
    TrackMidiEditScope,
)
from packages.music_core.midi_editing.plan_validator import (
    MidiEditPlanErrorCode,
    MidiEditPlanValidationError,
    OPERATION_APPLICABILITY,
    PlanValidator,
    validate_midi_edit_plan,
)


@dataclass(frozen=True)
class Context:
    ppq: int = 480
    is_drum: bool = False
    scope: MidiEditScope = TrackMidiEditScope(track_id="melody")


def plan_with(operation: dict[str, object], **plan_fields: object) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "summary": "Make a conservative edit",
        "operations": [operation],
        **plan_fields,
    }


VALID_OPERATIONS = [
    {"type": "transpose", "semitones": 5},
    {"type": "octave_shift", "octaves": -1},
    {"type": "velocity_set", "value": 96},
    {"type": "velocity_delta", "delta": -12},
    {"type": "velocity_scale", "factor": 1.25},
    {"type": "duration_scale", "factor": 0.75},
    {"type": "staccato", "ratio": 0.5},
    {"type": "legato", "overlap_ticks": 120},
    {"type": "quantize", "grid": "1/16", "strength": 0.75},
    {"type": "shift_timing", "delta_ticks": -60},
    {"type": "reduce_density", "keep_ratio": 0.6, "preserve_edges": False},
]


@pytest.mark.parametrize("operation", VALID_OPERATIONS, ids=lambda item: str(item["type"]))
def test_every_allowlisted_operation_parses_and_roundtrips(operation):
    parsed = PlanValidator.parse(plan_with(operation))
    reparsed = MidiEditPlan.model_validate_json(parsed.model_dump_json())
    assert reparsed == parsed
    assert reparsed.operations[0].type == operation["type"]


@pytest.mark.parametrize(
    ("operation_type", "field", "lower", "upper", "below", "above"),
    [
        ("transpose", "semitones", -24, 24, -25, 25),
        ("octave_shift", "octaves", -2, 2, -3, 3),
        ("velocity_set", "value", 1, 127, 0, 128),
        ("velocity_delta", "delta", -64, 64, -65, 65),
        ("velocity_scale", "factor", 0.25, 2.0, 0.249, 2.001),
        ("duration_scale", "factor", 0.25, 4.0, 0.249, 4.001),
        ("staccato", "ratio", 0.10, 0.95, 0.099, 0.951),
        ("legato", "overlap_ticks", 0, 1920, -1, 1921),
        ("quantize", "strength", 0.01, 1.0, 0.0, 1.001),
        ("reduce_density", "keep_ratio", 0.10, 0.95, 0.099, 0.951),
    ],
)
def test_static_numeric_boundaries(
    operation_type,
    field,
    lower,
    upper,
    below,
    above,
):
    defaults: dict[str, object] = {
        "quantize": {"grid": "1/16"},
    }.get(operation_type, {})
    for value in (lower, upper):
        PlanValidator.parse(plan_with({"type": operation_type, field: value, **defaults}))
    for value in (below, above):
        with pytest.raises(MidiEditPlanValidationError) as caught:
            PlanValidator.parse(plan_with({"type": operation_type, field: value, **defaults}))
        assert caught.value.code == MidiEditPlanErrorCode.INVALID_PARAMETER


@pytest.mark.parametrize(
    "operation",
    [
        {"type": "transpose", "semitones": 0},
        {"type": "octave_shift", "octaves": 0},
        {"type": "velocity_delta", "delta": 0},
        {"type": "velocity_scale", "factor": 1.0},
        {"type": "duration_scale", "factor": 1.0},
        {"type": "shift_timing", "delta_ticks": 0},
    ],
    ids=lambda item: str(item["type"]),
)
def test_static_noop_parameters_are_rejected(operation):
    with pytest.raises(MidiEditPlanValidationError) as caught:
        PlanValidator.parse(plan_with(operation))
    assert caught.value.code == MidiEditPlanErrorCode.INVALID_PARAMETER


@pytest.mark.parametrize("grid", ["1/4", "1/8", "1/16", "1/32"])
def test_quantize_grid_allowlist_and_defaults(grid):
    plan = PlanValidator.parse(plan_with({"type": "quantize", "grid": grid}))
    assert plan.operations[0].strength == 1.0


@pytest.mark.parametrize("grid", ["1/1", "1/2", "1/64", "eighth", 8])
def test_quantize_rejects_unknown_grid(grid):
    with pytest.raises(MidiEditPlanValidationError) as caught:
        PlanValidator.parse(plan_with({"type": "quantize", "grid": grid}))
    assert caught.value.code == MidiEditPlanErrorCode.INVALID_PARAMETER


def test_operation_defaults_are_stable():
    legato = PlanValidator.parse(plan_with({"type": "legato"})).operations[0]
    density = PlanValidator.parse(
        plan_with({"type": "reduce_density", "keep_ratio": 0.5})
    ).operations[0]
    assert legato.overlap_ticks == 0
    assert density.preserve_edges is True


def test_multiple_operations_keep_semantic_order_and_roundtrip():
    value = {
        "schema_version": "1.0",
        "summary": "Transpose, then quantize, then shape velocity",
        "operations": [
            {"type": "transpose", "semitones": 2},
            {"type": "quantize", "grid": "1/16"},
            {"type": "velocity_scale", "factor": 1.1},
        ],
    }
    plan = PlanValidator.parse_and_validate(value, Context())
    assert [operation.type for operation in plan.operations] == [
        "transpose",
        "quantize",
        "velocity_scale",
    ]
    assert MidiEditPlan.model_validate(plan.model_dump(mode="json")) == plan


@pytest.mark.parametrize(
    ("value", "code"),
    [
        (
            {
                "schema_version": "1.0",
                "summary": "Nothing",
                "operations": [],
            },
            MidiEditPlanErrorCode.EMPTY_PLAN,
        ),
        (
            {
                "schema_version": "1.0",
                "summary": "Too much",
                "operations": [{"type": "velocity_set", "value": 90}] * 9,
            },
            MidiEditPlanErrorCode.TOO_MANY_OPERATIONS,
        ),
        (plan_with({"type": "delete_all_tracks"}), MidiEditPlanErrorCode.UNKNOWN_OPERATION),
        (
            plan_with({"type": "velocity_set"}),
            MidiEditPlanErrorCode.INVALID_PARAMETER,
        ),
        (
            plan_with({"type": "velocity_set", "value": "100"}),
            MidiEditPlanErrorCode.INVALID_PARAMETER,
        ),
        (
            plan_with({"type": "velocity_set", "value": True}),
            MidiEditPlanErrorCode.INVALID_PARAMETER,
        ),
        (
            plan_with({"type": "velocity_set", "value": 90}, schema_version="1"),
            MidiEditPlanErrorCode.INVALID_PLAN,
        ),
        (
            plan_with({"type": "velocity_set", "value": 90}, summary="x" * 201),
            MidiEditPlanErrorCode.INVALID_PLAN,
        ),
        (
            plan_with({"type": "velocity_set", "value": 90}, summary="   "),
            MidiEditPlanErrorCode.INVALID_PLAN,
        ),
    ],
)
def test_plan_shape_and_limits_fail_closed(value, code):
    with pytest.raises(MidiEditPlanValidationError) as caught:
        PlanValidator.parse(value)
    assert caught.value.code == code
    assert caught.value.issues


def test_unknown_operation_value_is_not_reflected_in_safe_issues():
    injected = "execute_code:C:/secrets/.env"
    with pytest.raises(MidiEditPlanValidationError) as caught:
        PlanValidator.parse(plan_with({"type": injected}))
    assert caught.value.code == MidiEditPlanErrorCode.UNKNOWN_OPERATION
    assert injected not in repr(caught.value.issues)


@pytest.mark.parametrize(
    ("location", "field", "injected"),
    [
        ("plan", "songId", "song-elsewhere"),
        ("plan", "projectId", "other-project"),
        ("plan", "trackId", "drums"),
        ("plan", "noteIds", ["foreign-note"]),
        ("plan", "sectionId", "chorus"),
        ("operation", "trackId", "drums"),
        ("operation", "noteIds", ["foreign-note"]),
        ("operation", "path", "C:/secrets/.env"),
        ("operation", "url", "https://attacker.invalid"),
        ("operation", "shell", "rm -rf /"),
        ("operation", "code", "__import__('os').system('whoami')"),
        ("operation", "api_route", "/admin/delete"),
    ],
)
def test_authority_and_executable_field_injection_is_rejected(location, field, injected):
    value = plan_with({"type": "velocity_set", "value": 90})
    if location == "plan":
        value[field] = injected
    else:
        value["operations"][0][field] = injected
    with pytest.raises(MidiEditPlanValidationError) as caught:
        PlanValidator.parse(value)
    assert caught.value.code == MidiEditPlanErrorCode.INVALID_PLAN
    assert all(injected not in issue.values() for issue in caught.value.issues)


@pytest.mark.parametrize("invalid_number", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize(
    ("operation_type", "field"),
    [
        ("velocity_scale", "factor"),
        ("duration_scale", "factor"),
        ("staccato", "ratio"),
        ("quantize", "strength"),
        ("reduce_density", "keep_ratio"),
    ],
)
def test_non_finite_numbers_are_rejected(operation_type, field, invalid_number):
    operation: dict[str, object] = {"type": operation_type, field: invalid_number}
    if operation_type == "quantize":
        operation["grid"] = "1/16"
    with pytest.raises(MidiEditPlanValidationError) as caught:
        PlanValidator.parse(plan_with(operation))
    assert caught.value.code == MidiEditPlanErrorCode.INVALID_PARAMETER


@pytest.mark.parametrize("operation_type", ["transpose", "octave_shift"])
def test_drum_tracks_reject_pitch_operations_for_the_whole_plan(operation_type):
    parameter = {"transpose": {"semitones": 1}, "octave_shift": {"octaves": 1}}
    value = {
        "schema_version": "1.0",
        "summary": "One safe and one unsafe drum operation",
        "operations": [
            {"type": "velocity_set", "value": 100},
            {"type": operation_type, **parameter[operation_type]},
        ],
    }
    plan = PlanValidator.parse(value)
    with pytest.raises(MidiEditPlanValidationError) as caught:
        validate_midi_edit_plan(plan, Context(is_drum=True))
    assert caught.value.code == MidiEditPlanErrorCode.OPERATION_NOT_APPLICABLE
    assert caught.value.operation_index == 1
    assert caught.value.operation_type == operation_type
    assert len(plan.operations) == 2


@pytest.mark.parametrize(
    "operation",
    [operation for operation in VALID_OPERATIONS if operation["type"] not in {"transpose", "octave_shift"}],
    ids=lambda item: str(item["type"]),
)
def test_non_pitch_operations_apply_to_drum_tracks(operation):
    PlanValidator.parse_and_validate(plan_with(operation), Context(is_drum=True))


def test_contextual_ppq_limits_are_inclusive_and_reject_extremes():
    context = Context(ppq=480)
    for operation in (
        {"type": "legato", "overlap_ticks": 960},
        {"type": "shift_timing", "delta_ticks": 1920},
        {"type": "shift_timing", "delta_ticks": -1920},
    ):
        PlanValidator.parse_and_validate(plan_with(operation), context)

    for operation in (
        {"type": "legato", "overlap_ticks": 961},
        {"type": "shift_timing", "delta_ticks": 1921},
        {"type": "shift_timing", "delta_ticks": -(10**100)},
    ):
        with pytest.raises(MidiEditPlanValidationError) as caught:
            PlanValidator.parse_and_validate(plan_with(operation), context)
        assert caught.value.code == MidiEditPlanErrorCode.INVALID_PARAMETER


@pytest.mark.parametrize("invalid_ppq", [0, -1, True, 480.0])
def test_context_ppq_must_be_a_positive_integer(invalid_ppq):
    plan = PlanValidator.parse(plan_with({"type": "velocity_set", "value": 90}))
    with pytest.raises(MidiEditPlanValidationError) as caught:
        PlanValidator.validate(plan, Context(ppq=invalid_ppq))
    assert caught.value.code == MidiEditPlanErrorCode.INVALID_PLAN


def test_operation_applicability_is_complete_and_centralized():
    assert set(OPERATION_APPLICABILITY) == {item["type"] for item in VALID_OPERATIONS}
    for operation_type, applicability in OPERATION_APPLICABILITY.items():
        assert applicability.scope_types == {
            "selected_notes",
            "track",
            "section",
            "tick_range",
        }
        assert applicability.allows_pitched_track is True
        assert applicability.allows_drum_track is (
            operation_type not in {"transpose", "octave_shift"}
        )


def test_json_schema_is_closed_complete_and_discriminated():
    schema = MidiEditPlan.model_json_schema()
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["schema_version", "summary", "operations"]

    operation_items = schema["properties"]["operations"]["items"]
    discriminator = operation_items["discriminator"]
    assert discriminator["propertyName"] == "type"
    assert set(discriminator["mapping"]) == set(OPERATION_APPLICABILITY)
    assert len(operation_items["oneOf"]) == 11

    for definition in schema["$defs"].values():
        if isinstance(definition, dict) and definition.get("title", "").endswith(
            "MidiEditOperation"
        ):
            assert definition["additionalProperties"] is False
            assert "type" in definition["required"]


def test_validator_never_returns_a_partial_plan_after_late_failure():
    value = {
        "schema_version": "1.0",
        "summary": "Reject rather than dropping the last operation",
        "operations": [
            {"type": "velocity_delta", "delta": 5},
            {"type": "shift_timing", "delta_ticks": 1921},
        ],
    }
    with pytest.raises(MidiEditPlanValidationError) as caught:
        PlanValidator.parse_and_validate(value, Context(ppq=480))
    assert caught.value.operation_index == 1

    # The outer model is frozen, but Python list contents remain mutable. The
    # semantic boundary must revalidate instead of trusting a once-typed Plan.
    typed = PlanValidator.parse(plan_with({"type": "velocity_set", "value": 90}))
    typed.operations.clear()
    with pytest.raises(MidiEditPlanValidationError) as mutated:
        PlanValidator.validate(typed, Context())
    assert mutated.value.code == MidiEditPlanErrorCode.EMPTY_PLAN
