"""AI-assisted MIDI editing domain contracts (T35)."""

from packages.music_core.midi_editing.models import (
    MidiEditOperation,
    MidiEditPlan,
    MidiEditScope,
    SectionMidiEditScope,
    SelectedNotesMidiEditScope,
    TickRangeMidiEditScope,
    TrackMidiEditScope,
)
from packages.music_core.midi_editing.diff import (
    MidiNoteDiff,
    MidiNoteDiffError,
    MidiNoteDiffErrorCode,
    MidiNoteModificationDiff,
    calculate_midi_note_diff,
)
from packages.music_core.midi_editing.plan_validator import (
    MidiEditPlanErrorCode,
    MidiEditPlanValidationError,
    OPERATION_APPLICABILITY,
    PlanValidator,
    validate_midi_edit_plan,
)
from packages.music_core.midi_editing.scope import (
    canonical_scope_json,
    scope_fingerprint,
    select_scoped_notes,
)
from packages.music_core.midi_editing.transformer import (
    canonical_note_key,
    MidiTransformError,
    MidiTransformErrorCode,
    MidiTransformResult,
    MidiTransformWarning,
    MidiTransformWarningCode,
    round_half_away_from_zero,
    transform_midi_notes,
)

__all__ = [
    "MidiEditOperation",
    "MidiEditPlan",
    "MidiEditPlanErrorCode",
    "MidiEditPlanValidationError",
    "MidiEditScope",
    "MidiNoteDiff",
    "MidiNoteDiffError",
    "MidiNoteDiffErrorCode",
    "MidiNoteModificationDiff",
    "MidiTransformError",
    "MidiTransformErrorCode",
    "MidiTransformResult",
    "MidiTransformWarning",
    "MidiTransformWarningCode",
    "OPERATION_APPLICABILITY",
    "PlanValidator",
    "SectionMidiEditScope",
    "SelectedNotesMidiEditScope",
    "TickRangeMidiEditScope",
    "TrackMidiEditScope",
    "canonical_scope_json",
    "canonical_note_key",
    "calculate_midi_note_diff",
    "scope_fingerprint",
    "select_scoped_notes",
    "round_half_away_from_zero",
    "transform_midi_notes",
    "validate_midi_edit_plan",
]
