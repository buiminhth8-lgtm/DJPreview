"""Pure deterministic MIDI transforms for T35.3.

The transformer consumes resolved scoped notes only. It never reads Project state,
writes assets, calls a provider or mutates its inputs.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from fractions import Fraction

from pydantic import TypeAdapter, ValidationError

from packages.music_core.midi_editing.models import (
    DurationScaleMidiEditOperation,
    LegatoMidiEditOperation,
    MidiEditOperation,
    MidiEditPlan,
    MidiEditScope,
    OctaveShiftMidiEditOperation,
    QuantizeMidiEditOperation,
    ReduceDensityMidiEditOperation,
    ShiftTimingMidiEditOperation,
    StaccatoMidiEditOperation,
    TransposeMidiEditOperation,
    VelocityDeltaMidiEditOperation,
    VelocityScaleMidiEditOperation,
    VelocitySetMidiEditOperation,
)
from packages.music_core.midi_editing.plan_validator import PlanValidator
from services.api.schemas.midi_editor import MidiEditorNote

MAX_TRANSFORM_NOTES = 3000
MAX_TRANSFORMER_SEED = (2**32) - 1
_SCOPE_ADAPTER = TypeAdapter(MidiEditScope)


class MidiTransformErrorCode(StrEnum):
    INVALID_CONTEXT = "invalid_context"
    INVALID_SCOPED_NOTES = "invalid_scoped_notes"
    SCOPE_VIOLATION = "scope_violation"
    INVARIANT_VIOLATION = "invariant_violation"


class MidiTransformError(ValueError):
    """A transform failed atomically; no partial result is available."""

    def __init__(
        self,
        code: MidiTransformErrorCode,
        message: str,
        *,
        operation_index: int | None = None,
        operation_type: str | None = None,
        note_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.operation_index = operation_index
        self.operation_type = operation_type
        self.note_id = note_id


class MidiTransformWarningCode(StrEnum):
    PITCH_CLAMPED = "pitch_clamped"
    VELOCITY_CLAMPED = "velocity_clamped"
    START_TICK_CLAMPED = "start_tick_clamped"
    DURATION_CLAMPED = "duration_clamped"
    DURATION_MINIMUM_APPLIED = "duration_minimum_applied"


@dataclass(frozen=True)
class MidiTransformWarning:
    code: MidiTransformWarningCode
    operation_index: int
    operation_type: str
    note_id: str


@dataclass(frozen=True)
class MidiTransformResult:
    notes: tuple[MidiEditorNote, ...]
    removed_note_ids: tuple[str, ...]
    seed: int
    warnings: tuple[MidiTransformWarning, ...]


@dataclass(frozen=True)
class _TransformContext:
    scope: MidiEditScope
    ppq: int
    total_ticks: int
    is_drum: bool
    seed: int


@dataclass(frozen=True)
class _OperationResult:
    notes: tuple[MidiEditorNote, ...]
    warnings: tuple[tuple[MidiTransformWarningCode, str], ...] = ()


def _canonical_note_key(note: MidiEditorNote) -> tuple[int, int, int, str]:
    return (note.start_tick, note.pitch, note.channel, note.id)


def round_half_away_from_zero(value: Fraction) -> int:
    """Round an exact rational number without Python's bankers-round behavior."""
    if value >= 0:
        return (2 * value.numerator + value.denominator) // (2 * value.denominator)
    positive = -value
    return -((2 * positive.numerator + positive.denominator) // (2 * positive.denominator))


def _factor(value: float) -> Fraction:
    return Fraction(Decimal(str(value)))


def _clamp(value: int, lower: int, upper: int) -> int:
    return min(upper, max(lower, value))


def _scope_window(scope: MidiEditScope) -> tuple[int, int] | None:
    if scope.type in ("section", "tick_range"):
        return (scope.start_tick, scope.end_tick)
    return None


def _copy_note(note: MidiEditorNote, **changes: int) -> MidiEditorNote:
    return MidiEditorNote.model_validate({**note.model_dump(mode="python"), **changes})


def _scale_duration(
    notes: Sequence[MidiEditorNote],
    factor: Fraction,
    scope: MidiEditScope,
) -> _OperationResult:
    transformed: list[MidiEditorNote] = []
    warnings: list[tuple[MidiTransformWarningCode, str]] = []
    window = _scope_window(scope)
    for note in notes:
        raw_duration = round_half_away_from_zero(Fraction(note.duration_tick) * factor)
        duration = max(1, raw_duration)
        if duration != raw_duration:
            warnings.append((MidiTransformWarningCode.DURATION_MINIMUM_APPLIED, note.id))
        if window is not None:
            max_duration = window[1] - note.start_tick
            bounded = min(duration, max_duration)
            if bounded != duration:
                duration = bounded
                warnings.append((MidiTransformWarningCode.DURATION_CLAMPED, note.id))
        transformed.append(_copy_note(note, duration_tick=duration))
    return _OperationResult(tuple(transformed), tuple(warnings))


def apply_transpose(
    notes: Sequence[MidiEditorNote],
    operation: TransposeMidiEditOperation,
    context: _TransformContext,
) -> _OperationResult:
    transformed: list[MidiEditorNote] = []
    warnings: list[tuple[MidiTransformWarningCode, str]] = []
    for note in notes:
        raw_pitch = note.pitch + operation.semitones
        pitch = _clamp(raw_pitch, 0, 127)
        if pitch != raw_pitch:
            warnings.append((MidiTransformWarningCode.PITCH_CLAMPED, note.id))
        transformed.append(_copy_note(note, pitch=pitch))
    return _OperationResult(tuple(transformed), tuple(warnings))


def apply_octave_shift(
    notes: Sequence[MidiEditorNote],
    operation: OctaveShiftMidiEditOperation,
    context: _TransformContext,
) -> _OperationResult:
    return apply_transpose(
        notes,
        TransposeMidiEditOperation(type="transpose", semitones=operation.octaves * 12),
        context,
    )


def apply_velocity_set(
    notes: Sequence[MidiEditorNote],
    operation: VelocitySetMidiEditOperation,
    context: _TransformContext,
) -> _OperationResult:
    return _OperationResult(tuple(_copy_note(note, velocity=operation.value) for note in notes))


def apply_velocity_delta(
    notes: Sequence[MidiEditorNote],
    operation: VelocityDeltaMidiEditOperation,
    context: _TransformContext,
) -> _OperationResult:
    transformed: list[MidiEditorNote] = []
    warnings: list[tuple[MidiTransformWarningCode, str]] = []
    for note in notes:
        raw_velocity = note.velocity + operation.delta
        velocity = _clamp(raw_velocity, 1, 127)
        if velocity != raw_velocity:
            warnings.append((MidiTransformWarningCode.VELOCITY_CLAMPED, note.id))
        transformed.append(_copy_note(note, velocity=velocity))
    return _OperationResult(tuple(transformed), tuple(warnings))


def apply_velocity_scale(
    notes: Sequence[MidiEditorNote],
    operation: VelocityScaleMidiEditOperation,
    context: _TransformContext,
) -> _OperationResult:
    transformed: list[MidiEditorNote] = []
    warnings: list[tuple[MidiTransformWarningCode, str]] = []
    factor = _factor(operation.factor)
    for note in notes:
        raw_velocity = round_half_away_from_zero(Fraction(note.velocity) * factor)
        velocity = _clamp(raw_velocity, 1, 127)
        if velocity != raw_velocity:
            warnings.append((MidiTransformWarningCode.VELOCITY_CLAMPED, note.id))
        transformed.append(_copy_note(note, velocity=velocity))
    return _OperationResult(tuple(transformed), tuple(warnings))


def apply_duration_scale(
    notes: Sequence[MidiEditorNote],
    operation: DurationScaleMidiEditOperation,
    context: _TransformContext,
) -> _OperationResult:
    return _scale_duration(notes, _factor(operation.factor), context.scope)


def apply_staccato(
    notes: Sequence[MidiEditorNote],
    operation: StaccatoMidiEditOperation,
    context: _TransformContext,
) -> _OperationResult:
    return _scale_duration(notes, _factor(operation.ratio), context.scope)


def apply_legato(
    notes: Sequence[MidiEditorNote],
    operation: LegatoMidiEditOperation,
    context: _TransformContext,
) -> _OperationResult:
    next_onset: dict[tuple[int, int], int] = {}
    channels: dict[int, set[int]] = {}
    for note in notes:
        channels.setdefault(note.channel, set()).add(note.start_tick)
    for channel, onset_set in channels.items():
        onsets = sorted(onset_set)
        next_onset.update(
            ((channel, onset), following)
            for onset, following in zip(onsets, onsets[1:], strict=False)
        )

    transformed: list[MidiEditorNote] = []
    warnings: list[tuple[MidiTransformWarningCode, str]] = []
    window = _scope_window(context.scope)
    for note in notes:
        following = next_onset.get((note.channel, note.start_tick))
        if following is None:
            transformed.append(_copy_note(note))
            continue
        requested_duration = max(
            note.duration_tick,
            following + operation.overlap_ticks - note.start_tick,
        )
        duration = requested_duration
        if window is not None and requested_duration > note.duration_tick:
            duration = max(note.duration_tick, min(requested_duration, window[1] - note.start_tick))
        if duration != requested_duration:
            warnings.append((MidiTransformWarningCode.DURATION_CLAMPED, note.id))
        transformed.append(_copy_note(note, duration_tick=duration))
    return _OperationResult(tuple(transformed), tuple(warnings))


def _grid_ticks(ppq: int, grid: str) -> Fraction:
    denominator = int(grid.split("/", maxsplit=1)[1])
    return Fraction(ppq * 4, denominator)


def _nearest_grid_target(start_tick: int, grid_ticks: Fraction) -> Fraction:
    position = Fraction(start_tick, 1) / grid_ticks
    lower = position.numerator // position.denominator
    remainder = position - lower
    index = lower + (1 if remainder >= Fraction(1, 2) else 0)
    return index * grid_ticks


def apply_quantize(
    notes: Sequence[MidiEditorNote],
    operation: QuantizeMidiEditOperation,
    context: _TransformContext,
) -> _OperationResult:
    ticks = _grid_ticks(context.ppq, operation.grid)
    strength = _factor(operation.strength)
    window = _scope_window(context.scope)
    transformed: list[MidiEditorNote] = []
    warnings: list[tuple[MidiTransformWarningCode, str]] = []
    for note in notes:
        target = _nearest_grid_target(note.start_tick, ticks)
        interpolated = Fraction(note.start_tick) + (target - note.start_tick) * strength
        start_tick = round_half_away_from_zero(interpolated)
        if window is not None:
            bounded = _clamp(start_tick, window[0], window[1] - 1)
            if bounded != start_tick:
                start_tick = bounded
                warnings.append((MidiTransformWarningCode.START_TICK_CLAMPED, note.id))
        transformed.append(_copy_note(note, start_tick=start_tick))
    return _OperationResult(tuple(transformed), tuple(warnings))


def apply_shift_timing(
    notes: Sequence[MidiEditorNote],
    operation: ShiftTimingMidiEditOperation,
    context: _TransformContext,
) -> _OperationResult:
    window = _scope_window(context.scope)
    transformed: list[MidiEditorNote] = []
    warnings: list[tuple[MidiTransformWarningCode, str]] = []
    for note in notes:
        raw_start = note.start_tick + operation.delta_ticks
        start_tick = (
            _clamp(raw_start, window[0], window[1] - 1)
            if window is not None
            else max(0, raw_start)
        )
        if start_tick != raw_start:
            warnings.append((MidiTransformWarningCode.START_TICK_CLAMPED, note.id))
        transformed.append(_copy_note(note, start_tick=start_tick))
    return _OperationResult(tuple(transformed), tuple(warnings))


def _density_score(seed: int, note: MidiEditorNote) -> bytes:
    canonical = (
        f"{seed}|{note.id}|{note.pitch}|{note.start_tick}|{note.duration_tick}|"
        f"{note.velocity}|{note.channel}"
    )
    return hashlib.sha256(canonical.encode("utf-8")).digest()


def apply_reduce_density(
    notes: Sequence[MidiEditorNote],
    operation: ReduceDensityMidiEditOperation,
    context: _TransformContext,
) -> _OperationResult:
    ordered = sorted(notes, key=_canonical_note_key)
    keep_count = _clamp(
        round_half_away_from_zero(Fraction(len(ordered)) * _factor(operation.keep_ratio)),
        1,
        len(ordered),
    )
    forced_ids: set[str] = set()
    if operation.preserve_edges:
        forced_ids.add(ordered[0].id)
        forced_ids.add(ordered[-1].id)
        keep_count = max(keep_count, len(forced_ids))
    candidates = sorted(
        (note for note in ordered if note.id not in forced_ids),
        key=lambda note: (_density_score(context.seed, note), _canonical_note_key(note)),
    )
    kept_ids = forced_ids | {note.id for note in candidates[: keep_count - len(forced_ids)]}
    return _OperationResult(tuple(note for note in ordered if note.id in kept_ids))


_OperationHandler = Callable[
    [Sequence[MidiEditorNote], MidiEditOperation, _TransformContext],
    _OperationResult,
]
_OPERATION_HANDLERS: dict[str, _OperationHandler] = {
    "transpose": apply_transpose,
    "octave_shift": apply_octave_shift,
    "velocity_set": apply_velocity_set,
    "velocity_delta": apply_velocity_delta,
    "velocity_scale": apply_velocity_scale,
    "duration_scale": apply_duration_scale,
    "staccato": apply_staccato,
    "legato": apply_legato,
    "quantize": apply_quantize,
    "shift_timing": apply_shift_timing,
    "reduce_density": apply_reduce_density,
}


def _validate_transform_context(context: _TransformContext) -> None:
    if isinstance(context.total_ticks, bool) or not isinstance(context.total_ticks, int):
        raise MidiTransformError(MidiTransformErrorCode.INVALID_CONTEXT, "total_ticks 必须为整数")
    if context.total_ticks < 0:
        raise MidiTransformError(MidiTransformErrorCode.INVALID_CONTEXT, "total_ticks 不能为负数")
    if isinstance(context.seed, bool) or not isinstance(context.seed, int):
        raise MidiTransformError(MidiTransformErrorCode.INVALID_CONTEXT, "seed 必须为整数")
    if not 0 <= context.seed <= MAX_TRANSFORMER_SEED:
        raise MidiTransformError(
            MidiTransformErrorCode.INVALID_CONTEXT,
            "seed 必须为 unsigned 32-bit integer",
        )
    if context.scope.type in ("section", "tick_range") and context.scope.end_tick > context.total_ticks:
        raise MidiTransformError(
            MidiTransformErrorCode.INVALID_CONTEXT,
            "Scope 时间范围不能超过 total_ticks",
        )


def _validated_scope(scope: MidiEditScope) -> MidiEditScope:
    try:
        if not hasattr(scope, "model_dump"):
            raise TypeError("scope type")
        return _SCOPE_ADAPTER.validate_python(scope.model_dump(mode="python"), strict=True)
    except (AttributeError, TypeError, ValidationError, ValueError) as error:
        raise MidiTransformError(
            MidiTransformErrorCode.INVALID_CONTEXT,
            "Scope contract 无效",
        ) from error


def _validated_input_notes(
    notes: Sequence[MidiEditorNote],
    scope: MidiEditScope,
) -> tuple[MidiEditorNote, ...]:
    if not notes:
        raise MidiTransformError(
            MidiTransformErrorCode.INVALID_SCOPED_NOTES,
            "resolved scoped notes 不能为空",
        )
    if len(notes) > MAX_TRANSFORM_NOTES:
        raise MidiTransformError(
            MidiTransformErrorCode.INVALID_SCOPED_NOTES,
            f"resolved scoped notes 不能超过 {MAX_TRANSFORM_NOTES}",
        )
    copied: list[MidiEditorNote] = []
    try:
        for note in notes:
            if not isinstance(note, MidiEditorNote):
                raise TypeError("note type")
            copied.append(
                MidiEditorNote.model_validate(note.model_dump(mode="python"), strict=True)
            )
    except (TypeError, ValidationError, ValueError) as error:
        raise MidiTransformError(
            MidiTransformErrorCode.INVALID_SCOPED_NOTES,
            "resolved scoped notes 包含非法 Note",
        ) from error

    ids = [note.id for note in copied]
    if len(ids) != len(set(ids)):
        raise MidiTransformError(
            MidiTransformErrorCode.INVALID_SCOPED_NOTES,
            "resolved scoped notes 包含重复 Note ID",
        )
    supplied = set(ids)
    if scope.type == "selected_notes" and supplied != set(scope.note_ids):
        raise MidiTransformError(
            MidiTransformErrorCode.SCOPE_VIOLATION,
            "resolved Note IDs 与 selected_notes Scope 不一致",
        )
    if scope.type in ("section", "tick_range"):
        if any(not (scope.start_tick <= note.start_tick < scope.end_tick) for note in copied):
            raise MidiTransformError(
                MidiTransformErrorCode.SCOPE_VIOLATION,
                "resolved scoped notes 包含授权时间窗外 Note",
            )
    return tuple(sorted(copied, key=_canonical_note_key))


def _validate_step_invariants(
    before: Sequence[MidiEditorNote],
    after: Sequence[MidiEditorNote],
    *,
    scope: MidiEditScope,
    operation_index: int,
    operation_type: str,
) -> None:
    before_by_id = {note.id: note for note in before}
    after_ids = [note.id for note in after]
    if len(after_ids) != len(set(after_ids)) or not set(after_ids) <= set(before_by_id):
        raise MidiTransformError(
            MidiTransformErrorCode.SCOPE_VIOLATION,
            "operation 新增或复制了 Note ID",
            operation_index=operation_index,
            operation_type=operation_type,
        )
    if operation_type != "reduce_density" and set(after_ids) != set(before_by_id):
        raise MidiTransformError(
            MidiTransformErrorCode.SCOPE_VIOLATION,
            "非 density operation 删除了 Note",
            operation_index=operation_index,
            operation_type=operation_type,
        )
    for note in after:
        original = before_by_id[note.id]
        if note.channel != original.channel:
            raise MidiTransformError(
                MidiTransformErrorCode.INVARIANT_VIOLATION,
                "operation 修改了 Note channel",
                operation_index=operation_index,
                operation_type=operation_type,
                note_id=note.id,
            )
        values = (note.pitch, note.velocity, note.start_tick, note.duration_tick, note.channel)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise MidiTransformError(
                MidiTransformErrorCode.INVARIANT_VIOLATION,
                "operation 产生了非 integer MIDI value",
                operation_index=operation_index,
                operation_type=operation_type,
                note_id=note.id,
            )
        if not (
            0 <= note.pitch <= 127
            and 1 <= note.velocity <= 127
            and note.start_tick >= 0
            and note.duration_tick >= 1
            and 0 <= note.channel <= 15
        ):
            raise MidiTransformError(
                MidiTransformErrorCode.INVARIANT_VIOLATION,
                "operation 违反 MIDI Note invariant",
                operation_index=operation_index,
                operation_type=operation_type,
                note_id=note.id,
            )
        if scope.type in ("section", "tick_range") and not (
            scope.start_tick <= note.start_tick < scope.end_tick
        ):
            raise MidiTransformError(
                MidiTransformErrorCode.SCOPE_VIOLATION,
                "operation 将 Note onset 移出授权时间窗",
                operation_index=operation_index,
                operation_type=operation_type,
                note_id=note.id,
            )


def transform_midi_notes(
    notes: Sequence[MidiEditorNote],
    plan: MidiEditPlan,
    scope: MidiEditScope,
    *,
    ppq: int,
    total_ticks: int,
    is_drum: bool,
    seed: int,
) -> MidiTransformResult:
    """Apply a validated ordered Plan atomically to resolved scoped notes."""
    validated_scope = _validated_scope(scope)
    context = _TransformContext(
        scope=validated_scope,
        ppq=ppq,
        total_ticks=total_ticks,
        is_drum=is_drum,
        seed=seed,
    )
    _validate_transform_context(context)
    validated_plan = PlanValidator.validate(plan, context)
    current = _validated_input_notes(notes, validated_scope)
    original_ids = {note.id for note in current}
    warnings: list[MidiTransformWarning] = []

    for index, operation in enumerate(validated_plan.operations):
        handler = _OPERATION_HANDLERS[operation.type]
        operation_result = handler(current, operation, context)
        _validate_step_invariants(
            current,
            operation_result.notes,
            scope=validated_scope,
            operation_index=index,
            operation_type=operation.type,
        )
        warnings.extend(
            MidiTransformWarning(
                code=code,
                operation_index=index,
                operation_type=operation.type,
                note_id=note_id,
            )
            for code, note_id in operation_result.warnings
        )
        current = tuple(sorted(operation_result.notes, key=_canonical_note_key))

    output_ids = {note.id for note in current}
    final_notes = tuple(_copy_note(note) for note in current)
    return MidiTransformResult(
        notes=final_notes,
        removed_note_ids=tuple(sorted(original_ids - output_ids)),
        seed=seed,
        warnings=tuple(warnings),
    )
