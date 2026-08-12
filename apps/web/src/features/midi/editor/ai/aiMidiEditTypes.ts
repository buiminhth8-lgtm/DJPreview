import type { MidiEditorNote } from "../midiEditorTypes";

export interface SelectedNotesMidiEditScope {
  type: "selected_notes";
  trackId: string;
  noteIds: string[];
}

export interface TrackMidiEditScope {
  type: "track";
  trackId: string;
}

export interface SectionMidiEditScope {
  type: "section";
  trackId: string;
  sectionId: string;
  startTick: number;
  endTick: number;
}

export interface TickRangeMidiEditScope {
  type: "tick_range";
  trackId: string;
  startTick: number;
  endTick: number;
}

export type MidiEditScope =
  | SelectedNotesMidiEditScope
  | TrackMidiEditScope
  | SectionMidiEditScope
  | TickRangeMidiEditScope;

export interface AiMidiEditRequestIdentity {
  songId: string;
  baseVersionId: string;
  editorSessionId: string;
  draftRevision: number;
  scopeRevision: number;
  scopeFingerprint: string;
  trackId: string;
}

export interface CapturedMidiEditScope {
  scope: MidiEditScope;
  notes: MidiEditorNote[];
}
