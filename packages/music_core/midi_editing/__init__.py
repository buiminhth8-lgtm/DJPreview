"""AI-assisted MIDI editing domain contracts (T35)."""

from packages.music_core.midi_editing.models import (
    MidiEditScope,
    SectionMidiEditScope,
    SelectedNotesMidiEditScope,
    TickRangeMidiEditScope,
    TrackMidiEditScope,
)
from packages.music_core.midi_editing.scope import (
    canonical_scope_json,
    scope_fingerprint,
    select_scoped_notes,
)

__all__ = [
    "MidiEditScope",
    "SectionMidiEditScope",
    "SelectedNotesMidiEditScope",
    "TickRangeMidiEditScope",
    "TrackMidiEditScope",
    "canonical_scope_json",
    "scope_fingerprint",
    "select_scoped_notes",
]
