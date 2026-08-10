// features/midi/editor：MIDI Track Editor（T34.1 只读 read model）。
// 后续 T34.3+ 在此扩展编辑器 UI 组件。

export * from "./midiEditorTypes";
export { getMidiEditorDocument, mapMidiEditorDocument } from "./midiEditorApi";
export { useMidiEditorDocument } from "./useMidiEditorDocument";
export type { UseMidiEditorDocumentResult } from "./useMidiEditorDocument";
