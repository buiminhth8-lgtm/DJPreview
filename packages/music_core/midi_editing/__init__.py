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

__all__ = [
    "MidiEditOperation",
    "MidiEditPlan",
    "MidiEditPlanErrorCode",
    "MidiEditPlanValidationError",
    "MidiEditScope",
    "OPERATION_APPLICABILITY",
    "PlanValidator",
    "SectionMidiEditScope",
    "SelectedNotesMidiEditScope",
    "TickRangeMidiEditScope",
    "TrackMidiEditScope",
    "canonical_scope_json",
    "scope_fingerprint",
    "select_scoped_notes",
    "validate_midi_edit_plan",
]
