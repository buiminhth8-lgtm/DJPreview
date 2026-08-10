// features/midi/editor/PianoRollViewport.tsx（T34.3）
// 只读 Piano Roll：渲染选中 Track 的 Notes。
// - X 由 tick → pixel（pixelsPerTick）
// - Y 由 pitch → row（maxPitch 顶部）
// - React key = note.id（canonical）
// - click note → onSelectNote(note.id)（仅单选高亮，非编辑）

import { useMemo } from "react";
import type { MidiEditorNote } from "./midiEditorTypes";
import {
  computeMaxTick,
  computePitchRange,
  pitchToRow,
  rowToY,
  tickToBar,
  tickToBeat,
  tickToWidth,
  tickToX,
} from "./midiEditorLayout";
import { DEFAULT_LAYOUT } from "./midiEditorLayout";

export interface PianoRollViewportProps {
  notes: MidiEditorNote[];
  ppq: number;
  meter: { numerator: number; denominator: number };
  bpm: number | null;
  selectedNoteId: string | null;
  onSelectNote: (noteId: string | null) => void;
  layout?: typeof DEFAULT_LAYOUT;
}

export interface ViewNote {
  id: string;
  pitch: number;
  x: number;
  y: number;
  width: number;
  height: number;
  startTick: number;
  durationTick: number;
  velocity: number;
  channel: number;
}

export function computeViewNotes(
  notes: MidiEditorNote[],
  layout: typeof DEFAULT_LAYOUT,
): { viewNotes: ViewNote[]; minPitch: number; maxPitch: number; maxTick: number; height: number } {
  const { minPitch, maxPitch } = computePitchRange(notes);
  const maxTick = computeMaxTick(notes);
  const height = (maxPitch - minPitch + 1) * layout.rowHeight;
  const viewNotes = notes.map((note) => ({
    id: note.id,
    pitch: note.pitch,
    x: tickToX(note.startTick, layout),
    y: rowToY(pitchToRow(note.pitch, maxPitch), layout),
    width: tickToWidth(note.durationTick, layout),
    height: layout.rowHeight - 1,
    startTick: note.startTick,
    durationTick: note.durationTick,
    velocity: note.velocity,
    channel: note.channel,
  }));
  return { viewNotes, minPitch, maxPitch, maxTick, height };
}

export function PianoRollViewport({
  notes,
  ppq,
  meter,
  bpm,
  selectedNoteId,
  onSelectNote,
  layout = DEFAULT_LAYOUT,
}: PianoRollViewportProps) {
  const { viewNotes, minPitch, maxPitch, maxTick, height } = useMemo(
    () => computeViewNotes(notes, layout),
    [notes, layout],
  );

  const perBar = ppq * Math.max(1, meter.numerator);
  const bars = Math.max(4, Math.ceil((maxTick + 1) / perBar));
  const width = Math.max(1, bars * perBar * layout.pixelsPerTick);

  return (
    <div className="midi-editor__viewport">
      <svg
        className="midi-editor__roll"
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        data-ppq={ppq}
        data-note-count={notes.length}
      >
        {/* bar lines */}
        {Array.from({ length: bars + 1 }, (_, i) => (
          <line
            key={`barline-${i}`}
            x1={i * perBar * layout.pixelsPerTick}
            y1={0}
            x2={i * perBar * layout.pixelsPerTick}
            y2={height}
            stroke="rgba(255,255,255,0.1)"
            strokeWidth={1}
          />
        ))}
        {/* pitch row backgrounds */}
        {Array.from({ length: maxPitch - minPitch + 1 }, (_, i) => {
          const pitch = maxPitch - i;
          const isC = pitch % 12 === 0;
          return (
            <rect
              key={`row-${pitch}`}
              x={0}
              y={i * layout.rowHeight}
              width={width}
              height={layout.rowHeight}
              fill={isC ? "rgba(108,140,255,0.05)" : "transparent"}
            />
          );
        })}
        {/* notes */}
        {viewNotes.map((note) => (
          <rect
            key={note.id}
            className={`midi-editor__note${note.id === selectedNoteId ? " is-selected" : ""}`}
            x={note.x}
            y={note.y}
            width={note.width}
            height={note.height}
            rx={2}
            data-note-id={note.id}
            onClick={(e) => {
              e.stopPropagation();
              onSelectNote(note.id);
            }}
          >
            <title>{`pitch=${note.pitch} start=${note.startTick} dur=${note.durationTick}`}</title>
          </rect>
        ))}
      </svg>
      {notes.length === 0 && (
        <div className="midi-editor__empty-track">当前轨道没有音符</div>
      )}
      <div className="midi-editor__meta">
        {notes.length} notes · {ppq} PPQ · {meter.numerator}/{meter.denominator}
        {bpm != null ? ` · ${bpm} BPM` : ""}
      </div>
    </div>
  );
}

export { tickToBar, tickToBeat };
