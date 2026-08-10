// features/midi/editor：MIDI Track Editor。
// T34.1 read model；T34.3 editor shell + track selector + read-only piano roll。

export * from "./midiEditorTypes";
export { getMidiEditorDocument, mapMidiEditorDocument } from "./midiEditorApi";
export { useMidiEditorDocument } from "./useMidiEditorDocument";
export type { UseMidiEditorDocumentResult } from "./useMidiEditorDocument";
export { MidiEditor } from "./MidiEditor";
export { TrackSelector } from "./TrackSelector";
export { PianoRollViewport, computeViewNotes } from "./PianoRollViewport";
export { TimelineHeader } from "./TimelineHeader";
export { PianoKeyboard } from "./PianoKeyboard";
export * from "./midiEditorLayout";
