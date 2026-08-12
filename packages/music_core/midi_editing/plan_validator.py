"""Fail-closed parsing and contextual validation for T35 MIDI edit plans.

This module validates instructions only. It never resolves, mutates or returns MIDI
notes, and a Plan can never select its own Track or Note IDs.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol

from pydantic import ValidationError

from packages.music_core.midi_editing.models import MidiEditPlan, MidiEditScope


class MidiEditPlanErrorCode(StrEnum):
    INVALID_PLAN = "invalid_plan"
    UNKNOWN_OPERATION = "unknown_operation"
    INVALID_PARAMETER = "invalid_parameter"
    TOO_MANY_OPERATIONS = "too_many_operations"
    EMPTY_PLAN = "empty_plan"
    OPERATION_NOT_APPLICABLE = "operation_not_applicable"


class MidiEditPlanValidationError(ValueError):
    """Stable domain error raised when a whole Plan must be rejected."""

    def __init__(
        self,
        code: MidiEditPlanErrorCode,
        message: str,
        *,
        operation_index: int | None = None,
        operation_type: str | None = None,
        issues: tuple[dict[str, object], ...] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.operation_index = operation_index
        self.operation_type = operation_type
        self.issues = issues


class MidiEditPlanContext(Protocol):
    """Minimum authoritative context needed before a Plan may be transformed."""

    ppq: int
    is_drum: bool
    scope: MidiEditScope


@dataclass(frozen=True)
class OperationApplicability:
    scope_types: frozenset[str]
    allows_pitched_track: bool
    allows_drum_track: bool


_ALL_SCOPE_TYPES = frozenset({"selected_notes", "track", "section", "tick_range"})
_PITCHED_ONLY_OPERATIONS = frozenset({"transpose", "octave_shift"})
_OPERATION_TYPES = (
    "transpose",
    "octave_shift",
    "velocity_set",
    "velocity_delta",
    "velocity_scale",
    "duration_scale",
    "staccato",
    "legato",
    "quantize",
    "shift_timing",
    "reduce_density",
)

OPERATION_APPLICABILITY: Mapping[str, OperationApplicability] = MappingProxyType(
    {
        operation_type: OperationApplicability(
            scope_types=_ALL_SCOPE_TYPES,
            allows_pitched_track=True,
            allows_drum_track=operation_type not in _PITCHED_ONLY_OPERATIONS,
        )
        for operation_type in _OPERATION_TYPES
    }
)


def _safe_issues(error: ValidationError) -> tuple[dict[str, object], ...]:
    """Remove rejected input values before exposing validation diagnostics."""
    return tuple(
        {
            "type": issue["type"],
            "location": tuple(str(part) for part in issue["loc"]),
            "message": "schema constraint failed",
        }
        for issue in error.errors(include_url=False, include_input=False)
    )


def _schema_error_code(error: ValidationError) -> MidiEditPlanErrorCode:
    errors = error.errors(include_url=False, include_input=False)
    for issue in errors:
        if issue["loc"] == ("operations",) and issue["type"] == "too_short":
            return MidiEditPlanErrorCode.EMPTY_PLAN
    for issue in errors:
        if issue["loc"] == ("operations",) and issue["type"] == "too_long":
            return MidiEditPlanErrorCode.TOO_MANY_OPERATIONS
    if any(issue["type"] == "union_tag_invalid" for issue in errors):
        return MidiEditPlanErrorCode.UNKNOWN_OPERATION
    if any(issue["type"] == "extra_forbidden" for issue in errors):
        return MidiEditPlanErrorCode.INVALID_PLAN
    if any(issue["loc"] and issue["loc"][0] == "operations" for issue in errors):
        return MidiEditPlanErrorCode.INVALID_PARAMETER
    return MidiEditPlanErrorCode.INVALID_PLAN


class PlanValidator:
    """Parse schema-untrusted data and validate a typed Plan against Context."""

    @staticmethod
    def parse(value: object) -> MidiEditPlan:
        try:
            return MidiEditPlan.model_validate(value)
        except ValidationError as error:
            code = _schema_error_code(error)
            raise MidiEditPlanValidationError(
                code,
                f"MIDI edit Plan schema validation failed: {code.value}",
                issues=_safe_issues(error),
            ) from error

    @staticmethod
    def validate(plan: MidiEditPlan, context: MidiEditPlanContext) -> MidiEditPlan:
        # ``frozen=True`` prevents field reassignment but a Python list can still
        # be mutated in place. Re-parse the dump at this trust boundary so an
        # emptied/oversized/foreign operations list can never bypass the schema.
        plan = PlanValidator.parse(plan.model_dump(mode="python"))
        if isinstance(context.ppq, bool) or not isinstance(context.ppq, int) or context.ppq <= 0:
            raise MidiEditPlanValidationError(
                MidiEditPlanErrorCode.INVALID_PLAN,
                "MIDI edit Context ppq 必须为正整数",
            )
        if not isinstance(context.is_drum, bool):
            raise MidiEditPlanValidationError(
                MidiEditPlanErrorCode.INVALID_PLAN,
                "MIDI edit Context is_drum 必须为 boolean",
            )

        scope_type = context.scope.type
        for index, operation in enumerate(plan.operations):
            operation_type = operation.type
            applicability = OPERATION_APPLICABILITY[operation_type]
            if scope_type not in applicability.scope_types:
                raise MidiEditPlanValidationError(
                    MidiEditPlanErrorCode.OPERATION_NOT_APPLICABLE,
                    f"operation {operation_type} 不适用于 scope {scope_type}",
                    operation_index=index,
                    operation_type=operation_type,
                )
            if not context.is_drum and not applicability.allows_pitched_track:
                raise MidiEditPlanValidationError(
                    MidiEditPlanErrorCode.OPERATION_NOT_APPLICABLE,
                    f"operation {operation_type} 不适用于 pitched track",
                    operation_index=index,
                    operation_type=operation_type,
                )
            if context.is_drum and not applicability.allows_drum_track:
                raise MidiEditPlanValidationError(
                    MidiEditPlanErrorCode.OPERATION_NOT_APPLICABLE,
                    f"operation {operation_type} 不适用于 drum track",
                    operation_index=index,
                    operation_type=operation_type,
                )
            if operation_type == "legato" and operation.overlap_ticks > 2 * context.ppq:
                raise MidiEditPlanValidationError(
                    MidiEditPlanErrorCode.INVALID_PARAMETER,
                    "legato overlap_ticks 不能超过 2 * PPQ",
                    operation_index=index,
                    operation_type=operation_type,
                )
            if operation_type == "shift_timing" and abs(operation.delta_ticks) > 4 * context.ppq:
                raise MidiEditPlanValidationError(
                    MidiEditPlanErrorCode.INVALID_PARAMETER,
                    "shift_timing delta_ticks 绝对值不能超过 4 * PPQ",
                    operation_index=index,
                    operation_type=operation_type,
                )

        return plan

    @classmethod
    def parse_and_validate(
        cls,
        value: object,
        context: MidiEditPlanContext,
    ) -> MidiEditPlan:
        return cls.validate(cls.parse(value), context)


def validate_midi_edit_plan(
    plan: MidiEditPlan,
    context: MidiEditPlanContext,
) -> MidiEditPlan:
    """Functional entry point for callers that already hold a typed Plan."""
    return PlanValidator.validate(plan, context)
