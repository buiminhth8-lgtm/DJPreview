// features/midi/editor/PianoRollViewport.tsx（T34.8）
// Piano Roll pointer interaction priority: Space pan → note move/resize → empty-grid box select → double-click add.

import { memo, useCallback, useMemo, useRef, useState } from "react";
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
import {
  DEFAULT_SNAP,
  DEFAULT_NEW_NOTE_VELOCITY,
  getSnapTicks,
  midiPitchToNoteName,
  snapTick,
} from "./midiEditorGeometry";
import {
  clampBatchDelta,
  intentFromModifiers,
  intersectingNoteIds,
  type RectLike,
  type SelectionIntent,
} from "./midiSelection";

export interface PianoRollViewportProps {
  notes: MidiEditorNote[];
  ppq: number;
  meter: { numerator: number; denominator: number };
  bpm: number | null;
  channel: number;
  isDrum: boolean;
  snap: SnapValue;
  selectedNoteIds: ReadonlySet<string>;
  locked?: boolean;
  panEnabled?: boolean;
  onSelectNotes: (noteIds: string[], intent: SelectionIntent) => void;
  onAddNote: (note: Omit<MidiEditorNote, "id">) => void;
  onMoveNotes: (changes: Array<{ id: string; startTick: number; pitch: number }>) => void;
  onResizeNote: (noteId: string, newDurationTick: number) => void;
  onDragEnd?: () => void;
  onZoomH?: (dir: 1 | -1) => void;
  onScrollLeftChange?: (v: number) => void;
  onScrollTopChange?: (v: number) => void;
  gridRef?: (el: HTMLDivElement | null) => void;
  currentTick?: number;
  loopEnabled?: boolean;
  loopStartTick?: number;
  loopEndTick?: number;
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

interface NoteLayerProps {
  notes: ViewNote[];
  selectedNoteIds: ReadonlySet<string>;
  resizeEnabled: boolean;
  onPointerDown: (event: React.PointerEvent, note: ViewNote, kind: "move" | "resize") => void;
  onPointerMove: (event: React.PointerEvent) => void;
  onPointerEnd: (event: React.PointerEvent) => void;
}

const NoteLayer = memo(function NoteLayer({
  notes,
  selectedNoteIds,
  resizeEnabled,
  onPointerDown,
  onPointerMove,
  onPointerEnd,
}: NoteLayerProps) {
  return notes.map((note) => {
    const selected = selectedNoteIds.has(note.id);
    const showResize = resizeEnabled && (selectedNoteIds.size === 0 || selected);
    return (
      <g
        key={note.id}
        className={`midi-editor__note-group${selected ? " is-selected" : ""}`}
        data-note-id={note.id}
        onPointerDown={(event) => onPointerDown(event, note, "move")}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerEnd}
        onPointerCancel={onPointerEnd}
      >
        <rect
          className="midi-editor__note"
          x={note.x}
          y={note.y}
          width={Math.max(2, note.width - (showResize ? RESIZE_HANDLE_W : 0))}
          height={note.height}
          rx={2}
          style={{ cursor: "move" }}
        >
          <title>{`${midiPitchToNoteName(note.pitch)} start=${note.startTick} dur=${note.durationTick}`}</title>
        </rect>
        {showResize && (
          <rect
            className="midi-editor__resize"
            x={note.x + note.width - RESIZE_HANDLE_W}
            y={note.y}
            width={RESIZE_HANDLE_W}
            height={note.height}
            onPointerDown={(event) => onPointerDown(event, note, "resize")}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerEnd}
            onPointerCancel={onPointerEnd}
          />
        )}
      </g>
    );
  });
});

export function computeViewNotes(
  notes: MidiEditorNote[],
  layout: typeof DEFAULT_LAYOUT,
  fallbackPitchRange?: { minPitch: number; maxPitch: number },
): { viewNotes: ViewNote[]; minPitch: number; maxPitch: number; maxTick: number; height: number } {
  const range = notes.length ? computePitchRange(notes) : fallbackPitchRange ?? { minPitch: 48, maxPitch: 84 };
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

type DragState = {
  kind: "move" | "resize" | "pan" | "box";
  pointerId: number;
  startClientX: number;
  startClientY: number;
  moved: boolean;
  startScrollLeft: number;
  startScrollTop: number;
  noteId: string;
  startDuration: number;
  anchorStartTick: number;
  selectedOriginal: MidiEditorNote[];
  selectionIntent: SelectionIntent;
  boxStartX: number;
  boxStartY: number;
  collapseOnClick: boolean;
};

export function PianoRollViewport({
  notes,
  ppq,
  meter,
  bpm,
  channel,
  isDrum,
  snap = DEFAULT_SNAP,
  selectedNoteIds,
  locked = false,
  panEnabled = false,
  onSelectNotes,
  onAddNote,
  onMoveNotes,
  onResizeNote,
  onDragEnd,
  onZoomH,
  onScrollLeftChange,
  onScrollTopChange,
  gridRef,
  currentTick = 0,
  loopEnabled = false,
  loopStartTick = 0,
  loopEndTick = 0,
  layout = DEFAULT_LAYOUT,
}: PianoRollViewportProps) {
  const { viewNotes, minPitch, maxPitch, maxTick, height } = useMemo(
    () => computeViewNotes(notes, layout),
    [notes, layout],
  );
  const perBar = ticksPerBar(ppq, meter);
  const bars = Math.max(4, Math.ceil((Math.max(maxTick, currentTick, loopEndTick) + 1) / perBar));
  const width = Math.max(1, bars * perBar * layout.pixelsPerTick);
  const [selectionBox, setSelectionBox] = useState<RectLike | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const gridElRef = useRef<HTMLDivElement | null>(null);
  const panEnabledRef = useRef(false);
  panEnabledRef.current = panEnabled;

  const setGridRef = (element: HTMLDivElement | null) => {
    gridElRef.current = element;
    gridRef?.(element);
  };

  const capturePointer = (event: React.PointerEvent) => {
    const element = event.currentTarget as Element & { setPointerCapture?: (pointerId: number) => void };
    try {
      element.setPointerCapture?.(event.pointerId);
    } catch {
      // Pointer capture is unavailable in jsdom and can fail after DOM changes.
    }
  };

  const beginPan = useCallback((event: React.PointerEvent) => {
    event.preventDefault();
    event.stopPropagation();
    capturePointer(event);
    dragRef.current = {
      kind: "pan",
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      moved: false,
      startScrollLeft: gridElRef.current?.scrollLeft ?? 0,
      startScrollTop: gridElRef.current?.scrollTop ?? 0,
      noteId: "",
      startDuration: 0,
      anchorStartTick: 0,
      selectedOriginal: [],
      selectionIntent: "replace",
      boxStartX: 0,
      boxStartY: 0,
      collapseOnClick: false,
    };
  }, []);

  const onNotePointerDown = useCallback(
    (event: React.PointerEvent, note: ViewNote, kind: "move" | "resize") => {
      if (event.button !== 0) return;
      if (panEnabledRef.current) {
        beginPan(event);
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      const intent = intentFromModifiers({
        primary: event.ctrlKey || event.metaKey,
        shift: event.shiftKey,
      });
      const alreadySelected = selectedNoteIds.has(note.id);
      if (intent !== "replace") {
        onSelectNotes([note.id], intent);
        return;
      }
      if (!alreadySelected) onSelectNotes([note.id], "replace");
      if (locked) return;
      if (kind === "resize" && selectedNoteIds.size > 1) return;

      const movingIds = alreadySelected ? selectedNoteIds : new Set([note.id]);
      const selectedOriginal = notes.filter((candidate) => movingIds.has(candidate.id));
      capturePointer(event);
      dragRef.current = {
        kind,
        pointerId: event.pointerId,
        startClientX: event.clientX,
        startClientY: event.clientY,
        moved: false,
        startScrollLeft: 0,
        startScrollTop: 0,
        noteId: note.id,
        startDuration: note.durationTick,
        anchorStartTick: note.startTick,
        selectedOriginal,
        selectionIntent: "replace",
        boxStartX: 0,
        boxStartY: 0,
        collapseOnClick: alreadySelected && selectedNoteIds.size > 1,
      };
    },
    [beginPan, locked, notes, onSelectNotes, selectedNoteIds],
  );

  const onPointerMove = useCallback(
    (event: React.PointerEvent) => {
      const drag = dragRef.current;
      if (!drag || drag.pointerId !== event.pointerId) return;
      const dx = event.clientX - drag.startClientX;
      const dy = event.clientY - drag.startClientY;
      if (!drag.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD_PX) return;
      drag.moved = true;

      if (drag.kind === "pan") {
        const element = gridElRef.current;
        if (!element) return;
        element.scrollLeft = Math.max(0, drag.startScrollLeft - dx);
        element.scrollTop = Math.max(0, drag.startScrollTop - dy);
        onScrollLeftChange?.(element.scrollLeft);
        onScrollTopChange?.(element.scrollTop);
        return;
      }
      if (drag.kind === "box") {
        const element = gridElRef.current;
        if (!element) return;
        const rect = element.getBoundingClientRect();
        setSelectionBox({
          x: drag.boxStartX,
          y: drag.boxStartY,
          width: event.clientX - rect.left + element.scrollLeft - drag.boxStartX,
          height: event.clientY - rect.top + element.scrollTop - drag.boxStartY,
        });
        return;
      }
      if (drag.kind === "move") {
        const rawDelta = Math.round(dx / layout.pixelsPerTick);
        const snappedAnchor = snapTick(drag.anchorStartTick + rawDelta, snap, ppq);
        const desiredPitchDelta = -Math.round(dy / layout.rowHeight);
        const { tickDelta, pitchDelta } = clampBatchDelta(
          drag.selectedOriginal,
          snappedAnchor - drag.anchorStartTick,
          desiredPitchDelta,
        );
        onMoveNotes(
          drag.selectedOriginal.map((note) => ({
            id: note.id,
            startTick: note.startTick + tickDelta,
            pitch: note.pitch + pitchDelta,
          })),
        );
        return;
      }
      const duration = Math.max(1, drag.startDuration + Math.round(dx / layout.pixelsPerTick));
      const snappedEnd = snapTick(drag.anchorStartTick + duration, snap, ppq);
      onResizeNote(drag.noteId, Math.max(1, snappedEnd - drag.anchorStartTick));
    },
    [layout.pixelsPerTick, layout.rowHeight, onMoveNotes, onResizeNote, onScrollLeftChange, onScrollTopChange, ppq, snap],
  );

  const endDrag = useCallback(
    (event: React.PointerEvent) => {
      const drag = dragRef.current;
      if (!drag || drag.pointerId !== event.pointerId) return;
      dragRef.current = null;
      if (drag.kind === "box") {
        if (drag.moved && selectionBox) {
          onSelectNotes(intersectingNoteIds(viewNotes, selectionBox), drag.selectionIntent);
        } else if (drag.selectionIntent === "replace") {
          onSelectNotes([], "replace");
        }
        setSelectionBox(null);
        return;
      }
      if (drag.kind === "move" && !drag.moved && drag.collapseOnClick) {
        onSelectNotes([drag.noteId], "replace");
      }
      if ((drag.kind === "move" || drag.kind === "resize") && drag.moved) onDragEnd?.();
    },
    [onDragEnd, onSelectNotes, selectionBox, viewNotes],
  );

  const onGridDoubleClick = (event: React.MouseEvent) => {
    if (locked || panEnabledRef.current) return;
    const target = event.target as Element;
    if (target.closest?.("[data-note-id]")) return;
    const element = gridElRef.current;
    if (!element) return;
    const rect = element.getBoundingClientRect();
    const rawTick = (event.clientX - rect.left + element.scrollLeft) / layout.pixelsPerTick;
    const startTick = snapTick(Math.max(0, Math.round(rawTick)), snap, ppq);
    const row = Math.floor((event.clientY - rect.top + element.scrollTop) / layout.rowHeight);
    const pitch = Math.max(0, Math.min(127, maxPitch - row));
    onAddNote({
      pitch,
      startTick,
      durationTick: getSnapTicks(snap, ppq),
      velocity: DEFAULT_NEW_NOTE_VELOCITY,
      channel,
    });
  };

  const onGridPointerDown = (event: React.PointerEvent) => {
    if (event.button !== 0) return;
    const target = event.target as Element;
    if (target.closest?.("[data-note-id]")) return;
    if (panEnabledRef.current) {
      beginPan(event);
      return;
    }
    const element = gridElRef.current;
    if (!element) return;
    const rect = element.getBoundingClientRect();
    const x = event.clientX - rect.left + element.scrollLeft;
    const y = event.clientY - rect.top + element.scrollTop;
    const intent = intentFromModifiers({ primary: event.ctrlKey || event.metaKey, shift: event.shiftKey });
    capturePointer(event);
    dragRef.current = {
      kind: "box",
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      moved: false,
      startScrollLeft: element.scrollLeft,
      startScrollTop: element.scrollTop,
      noteId: "",
      startDuration: 0,
      anchorStartTick: 0,
      selectedOriginal: [],
      selectionIntent: intent,
      boxStartX: x,
      boxStartY: y,
      collapseOnClick: false,
    };
    setSelectionBox({ x, y, width: 0, height: 0 });
  };

  const onWheel = (event: React.WheelEvent) => {
    if (event.ctrlKey || event.metaKey) {
      event.preventDefault();
      onZoomH?.(event.deltaY < 0 ? 1 : -1);
      return;
    }
    const element = gridElRef.current;
    if (!element) return;
    if (event.shiftKey) {
      element.scrollLeft += event.deltaY;
      onScrollLeftChange?.(element.scrollLeft);
    } else {
      element.scrollTop += event.deltaY;
      onScrollTopChange?.(element.scrollTop);
    }
  };

  return (
    <div className="midi-editor__viewport">
      <div
        ref={setGridRef}
        className={`midi-editor__grid${locked ? " is-locked" : ""}${panEnabled ? " is-pan" : ""}`}
        style={{ position: "relative", overflow: "auto" }}
        onDoubleClick={onGridDoubleClick}
        onPointerDown={onGridPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onWheel={onWheel}
        onScroll={(event) => {
          onScrollLeftChange?.(event.currentTarget.scrollLeft);
          onScrollTopChange?.(event.currentTarget.scrollTop);
        }}
      >
        <svg
          className="midi-editor__roll"
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          data-ppq={ppq}
          data-note-count={notes.length}
        >
          {loopEnabled && loopEndTick > loopStartTick && (
            <rect
              className="midi-editor__roll-loop-region"
              data-testid="roll-loop-region"
              x={loopStartTick * layout.pixelsPerTick}
              y={0}
              width={(loopEndTick - loopStartTick) * layout.pixelsPerTick}
              height={height}
            />
          )}
          {Array.from({ length: bars + 1 }, (_, index) => (
            <line
              key={`barline-${index}`}
              x1={index * perBar * layout.pixelsPerTick}
              y1={0}
              x2={index * perBar * layout.pixelsPerTick}
              y2={height}
              stroke="rgba(255,255,255,0.12)"
            />
          ))}
          {Array.from({ length: bars * meter.numerator }, (_, index) => (
            <line
              key={`beat-${index}`}
              x1={index * ppq * layout.pixelsPerTick}
              y1={0}
              x2={index * ppq * layout.pixelsPerTick}
              y2={height}
              stroke="rgba(255,255,255,0.05)"
            />
          ))}
          {Array.from({ length: maxPitch - minPitch + 1 }, (_, index) => {
            const pitch = maxPitch - index;
            return (
              <rect
                key={`row-${pitch}`}
                x={0}
                y={index * layout.rowHeight}
                width={width}
                height={layout.rowHeight}
                fill={pitch % 12 === 0 ? "rgba(108,140,255,0.06)" : "transparent"}
              />
            );
          })}
          <NoteLayer
            notes={viewNotes}
            selectedNoteIds={selectedNoteIds}
            resizeEnabled={selectedNoteIds.size <= 1}
            onPointerDown={onNotePointerDown}
            onPointerMove={onPointerMove}
            onPointerEnd={endDrag}
          />
          {selectionBox && (
            <rect
              className="midi-editor__selection-box"
              data-testid="selection-box"
              x={Math.min(selectionBox.x, selectionBox.x + selectionBox.width)}
              y={Math.min(selectionBox.y, selectionBox.y + selectionBox.height)}
              width={Math.abs(selectionBox.width)}
              height={Math.abs(selectionBox.height)}
            />
          )}
          <line
            className="midi-editor__roll-playhead"
            data-testid="roll-playhead"
            x1={currentTick * layout.pixelsPerTick}
            y1={0}
            x2={currentTick * layout.pixelsPerTick}
            y2={height}
          />
        </svg>
        {notes.length === 0 && <div className="midi-editor__empty-track">当前轨道没有音符，双击空白添加</div>}
      </div>
      <div className="midi-editor__meta">
        {notes.length} notes · {ppq} PPQ · {meter.numerator}/{meter.denominator}
        {bpm != null ? ` · ${bpm} BPM` : ""} · {isDrum ? "drum" : `channel ${channel}`}
      </div>
    </div>
  );
}

export { tickToBar, tickToBeat };
