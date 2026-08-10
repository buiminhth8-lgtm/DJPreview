// features/midi/editor/PianoRollViewport.tsx（T34.4）
// 可编辑 Piano Roll Draft 视图：
// - X 由 tick → pixel；Y 由 pitch → row
// - 单击 Note → 选中；双击空白 → 新增 Note
// - 拖 Note 主体 → Move（startTick/pitch）；拖右边缘 → Resize（durationTick）
// - 所有操作走 draft 回调；不直接调用 backend
// - React key / data-note-id = canonical note.id（新增为 draft:uuid 临时 id）

import { useMemo, useRef } from "react";
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
  DEFAULT_LAYOUT,
  ticksPerBar,
} from "./midiEditorLayout";
import type { SnapValue } from "./midiEditorGeometry";
import { DEFAULT_SNAP, DEFAULT_NEW_NOTE_VELOCITY, midiPitchToNoteName, snapTick } from "./midiEditorGeometry";

export interface PianoRollViewportProps {
  notes: MidiEditorNote[];
  ppq: number;
  meter: { numerator: number; denominator: number };
  bpm: number | null;
  channel: number;
  isDrum: boolean;
  snap: SnapValue;
  selectedNoteId: string | null;
  locked?: boolean;
  panEnabled?: boolean;
  onSelectNote: (noteId: string | null) => void;
  onAddNote: (note: Omit<MidiEditorNote, "id">) => void;
  onMoveNote: (noteId: string, newStartTick: number, newPitch: number) => void;
  onResizeNote: (noteId: string, newDurationTick: number) => void;
  onZoomH?: (dir: 1 | -1) => void;
  onScrollLeftChange?: (v: number) => void;
  onScrollTopChange?: (v: number) => void;
  gridRef?: (el: HTMLDivElement | null) => void;
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

const DRAG_THRESHOLD_PX = 3;
const RESIZE_HANDLE_W = 6;

export function computeViewNotes(
  notes: MidiEditorNote[],
  layout: typeof DEFAULT_LAYOUT,
  fallbackPitchRange?: { minPitch: number; maxPitch: number },
): { viewNotes: ViewNote[]; minPitch: number; maxPitch: number; maxTick: number; height: number } {
  const range = notes.length
    ? computePitchRange(notes)
    : fallbackPitchRange ?? { minPitch: 48, maxPitch: 84 };
  const { minPitch, maxPitch } = range;
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
  channel,
  isDrum,
  snap = DEFAULT_SNAP,
  selectedNoteId,
  locked = false,
  panEnabled = false,
  onSelectNote,
  onAddNote,
  onMoveNote,
  onResizeNote,
  onZoomH,
  onScrollLeftChange,
  onScrollTopChange,
  gridRef,
  layout = DEFAULT_LAYOUT,
}: PianoRollViewportProps) {
  const { viewNotes, minPitch, maxPitch, maxTick, height } = useMemo(
    () => computeViewNotes(notes, layout),
    [notes, layout],
  );

  const perBar = ticksPerBar(ppq, meter);
  const bars = Math.max(4, Math.ceil((maxTick + 1) / perBar));
  const width = Math.max(1, bars * perBar * layout.pixelsPerTick);

  // drag state
  const dragRef = useRef<{
    kind: "move" | "resize" | "pan" | null;
    pointerId: number;
    startClientX: number;
    startClientY: number;
    startTick: number;
    startPitch: number;
    startDuration: number;
    noteId: string;
    moved: boolean;
    startScrollLeft: number;
    startScrollTop: number;
  } | null>(null);
  const gridElRef = useRef<HTMLDivElement | null>(null);
  const panEnabledRef = useRef(false);
  panEnabledRef.current = panEnabled;

  const setGridRef = (el: HTMLDivElement | null) => {
    gridElRef.current = el;
    gridRef?.(el);
  };

  const onPointerDown = (e: React.PointerEvent, note: ViewNote, kind: "move" | "resize") => {
    if (locked) return; // lock blocks edit handlers
    e.preventDefault();
    e.stopPropagation();
    onSelectNote(note.id);
    const el = e.currentTarget as SVGElement;
    if (typeof el.setPointerCapture === "function") {
      try {
        el.setPointerCapture(e.pointerId);
      } catch {
        // ignore
      }
    }
    dragRef.current = {
      kind,
      pointerId: e.pointerId,
      startClientX: e.clientX,
      startClientY: e.clientY,
      startTick: note.startTick,
      startPitch: note.pitch,
      startDuration: note.durationTick,
      noteId: note.id,
      moved: false,
      startScrollLeft: 0,
      startScrollTop: 0,
    };
  };

  const onPointerMove = (e: React.PointerEvent) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== e.pointerId) return;
    const dx = e.clientX - drag.startClientX;
    const dy = e.clientY - drag.startClientY;
    if (!drag.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD_PX) return;
    drag.moved = true;

    if (drag.kind === "pan") {
      const el = gridElRef.current;
      if (!el) return;
      el.scrollLeft = Math.max(0, drag.startScrollLeft - dx);
      el.scrollTop = Math.max(0, drag.startScrollTop - dy);
      onScrollLeftChange?.(el.scrollLeft);
      onScrollTopChange?.(el.scrollTop);
      return;
    }

    if (drag.kind === "move") {
      const dt = Math.round(dx / layout.pixelsPerTick);
      const dp = Math.round(dy / layout.rowHeight);
      const newStart = snapTick(Math.max(0, drag.startTick + dt), snap, ppq);
      const newPitch = Math.max(0, Math.min(127, drag.startPitch - dp));
      onMoveNote(drag.noteId, newStart, newPitch);
    } else if (drag.kind === "resize") {
      const dt = Math.round(dx / layout.pixelsPerTick);
      const newDur = Math.max(1, drag.startDuration + dt);
      onResizeNote(drag.noteId, newDur);
    }
  };

  const endDrag = (e: React.PointerEvent) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== e.pointerId) return;
    dragRef.current = null;
    const el = e.currentTarget as SVGElement;
    if (typeof el.releasePointerCapture === "function") {
      try {
        el.releasePointerCapture(e.pointerId);
      } catch {
        // ignore
      }
    }
  };

  const onGridDoubleClick = (e: React.MouseEvent) => {
    if (locked) return; // lock blocks add
    const el = gridElRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const rawTick = (e.clientX - rect.left + el.scrollLeft) / layout.pixelsPerTick;
    const startTick = snapTick(Math.max(0, Math.round(rawTick)), snap, ppq);
    const row = Math.floor((e.clientY - rect.top + el.scrollTop) / layout.rowHeight);
    const pitch = Math.max(0, Math.min(127, maxPitch - row));
    const snapUnit = snap === "off" ? Math.max(1, Math.round(ppq / 4)) : Math.max(1, Math.round((ppq * 4) / (snapDivisor(snap) * 4)));
    onAddNote({
      pitch,
      startTick,
      durationTick: snapUnit,
      velocity: DEFAULT_NEW_NOTE_VELOCITY,
      channel,
    });
    onSelectNote(null);
  };

  const onGridPointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    // Space + drag → pan（允许 Select；不允许 add/move）
    if (e.currentTarget === e.target) {
      onSelectNote(null);
    }
    if (panEnabledRef.current) {
      e.preventDefault();
      dragRef.current = {
        kind: "pan",
        pointerId: e.pointerId,
        startClientX: e.clientX,
        startClientY: e.clientY,
        startTick: 0,
        startPitch: 0,
        startDuration: 0,
        noteId: "",
        moved: false,
        startScrollLeft: gridElRef.current?.scrollLeft ?? 0,
        startScrollTop: gridElRef.current?.scrollTop ?? 0,
      };
    }
  };

  const onGridPointerMove = (e: React.PointerEvent) => onPointerMove(e);
  const onGridPointerUp = (e: React.PointerEvent) => endDrag(e);

  const onWheel = (e: React.WheelEvent) => {
    // Ctrl/Cmd + wheel → horizontal zoom；Shift + wheel → horizontal scroll；else vertical scroll
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      onZoomH?.(e.deltaY < 0 ? 1 : -1);
      return;
    }
    const el = gridElRef.current;
    if (!el) return;
    if (e.shiftKey) {
      el.scrollLeft += e.deltaY;
      onScrollLeftChange?.(el.scrollLeft);
    } else {
      el.scrollTop += e.deltaY;
      onScrollTopChange?.(el.scrollTop);
    }
  };

  return (
    <div className="midi-editor__viewport">
      <div
        ref={setGridRef}
        className={`midi-editor__grid${locked ? " is-locked" : ""}${panEnabled ? " is-pan" : ""}`}
        style={{ position: "relative", overflow: "hidden" }}
        onDoubleClick={onGridDoubleClick}
        onPointerDown={onGridPointerDown}
        onPointerMove={onGridPointerMove}
        onPointerUp={onGridPointerUp}
        onPointerCancel={onGridPointerUp}
        onWheel={onWheel}
      >
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
              stroke="rgba(255,255,255,0.12)"
              strokeWidth={1}
            />
          ))}
          {/* beat lines */}
          {Array.from({ length: bars * meter.numerator }, (_, i) => (
            <line
              key={`beat-${i}`}
              x1={i * ppq * layout.pixelsPerTick}
              y1={0}
              x2={i * ppq * layout.pixelsPerTick}
              y2={height}
              stroke="rgba(255,255,255,0.05)"
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
                fill={isC ? "rgba(108,140,255,0.06)" : "transparent"}
              />
            );
          })}
          {/* notes */}
          {viewNotes.map((note) => (
            <g
              key={note.id}
              className={`midi-editor__note-group${note.id === selectedNoteId ? " is-selected" : ""}`}
              data-note-id={note.id}
              onPointerDown={(e) => onPointerDown(e, note, "move")}
              onPointerMove={onPointerMove}
              onPointerUp={endDrag}
              onPointerCancel={endDrag}
            >
              <rect
                className="midi-editor__note"
                x={note.x}
                y={note.y}
                width={Math.max(2, note.width - RESIZE_HANDLE_W)}
                height={note.height}
                rx={2}
                fill="#6c8cff"
                opacity={0.9}
                style={{ cursor: "move" }}
              >
                <title>{`${midiPitchToNoteName(note.pitch)} start=${note.startTick} dur=${note.durationTick}`}</title>
              </rect>
              <rect
                className="midi-editor__resize"
                x={note.x + note.width - RESIZE_HANDLE_W}
                y={note.y}
                width={RESIZE_HANDLE_W}
                height={note.height}
                fill="rgba(34,211,238,0.6)"
                style={{ cursor: "ew-resize" }}
                onPointerDown={(e) => onPointerDown(e, note, "resize")}
                onPointerMove={onPointerMove}
                onPointerUp={endDrag}
                onPointerCancel={endDrag}
              />
            </g>
          ))}
        </svg>
        {notes.length === 0 && (
          <div className="midi-editor__empty-track">当前轨道没有音符，双击空白添加</div>
        )}
      </div>
      <div className="midi-editor__meta">
        {notes.length} notes · {ppq} PPQ · {meter.numerator}/{meter.denominator}
        {bpm != null ? ` · ${bpm} BPM` : ""} · {isDrum ? "drum" : "channel " + channel}
      </div>
    </div>
  );
}

function snapDivisor(snap: SnapValue): number {
  switch (snap) {
    case "1/1":
      return 0.25;
    case "1/2":
      return 0.5;
    case "1/4":
      return 1;
    case "1/8":
      return 2;
    case "1/16":
      return 4;
    case "1/32":
      return 8;
    default:
      return 1;
  }
}

export { tickToBar, tickToBeat };
