// features/midi/editor/midiEditorTypes.ts（T34.1）
// MIDI 编辑器文档类型（只读 read model）。
// Canonical 时间 = integer MIDI tick；Track/Note ID 稳定（来自后端）。

export interface MidiEditorNote {
  id: string;
  pitch: number; // 0..127
  startTick: number; // >= 0
  durationTick: number; // > 0
  velocity: number; // 1..127
  channel: number; // 0..15
}

export interface MidiEditorTrack {
  id: string; // MusicSpec track.id（稳定）
  role: string | null;
  name: string;
  channel: number;
  instrument: string | null;
  isDrum: boolean;
  notes: MidiEditorNote[];
}

export interface MidiEditorDocument {
  songId: string;
  versionId: string | null;
  ppq: number; // > 0
  bpm: number | null;
  timeSignature: [number, number];
  totalBars: number;
  tracks: MidiEditorTrack[];
}
