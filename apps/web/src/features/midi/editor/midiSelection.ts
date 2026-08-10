import type { MidiEditorNote } from "./midiEditorTypes";

export type SelectionIntent = "replace" | "toggle" | "append";

export interface SelectionModifiers {
  primary: boolean;
  shift: boolean;
}

export interface RectLike {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface PositionedNote extends RectLike {
  id: string;
}

export interface MidiClipboardNote {
  pitch: number;
  relativeStartTick: number;
  durationTick: number;
  velocity: number;
}

export interface MidiClipboard {
  sourceKind: "drum" | "pitched";
  notes: MidiClipboardNote[];
}

export interface SelectedNoteSummary {
  count: number;
  startTick: number;
  endTick: number;
  minPitch: number;
  maxPitch: number;
  averageVelocity: number;
}

export function intentFromModifiers(modifiers: SelectionModifiers): SelectionIntent {
  if (modifiers.primary) return "toggle";
  if (modifiers.shift) return "append";
  return "replace";
}

export function applySelection(
  current: ReadonlySet<string>,
  noteIds: Iterable<string>,
  intent: SelectionIntent,
): Set<string> {
  const ids = Array.from(noteIds);
  if (intent === "replace") return new Set(ids);
  const next = new Set(current);
  for (const id of ids) {
    if (intent === "toggle" && next.has(id)) next.delete(id);
    else next.add(id);
  }
  return next;
}

export function intersectingNoteIds(notes: PositionedNote[], rect: RectLike): string[] {
  const left = Math.min(rect.x, rect.x + rect.width);
  const right = Math.max(rect.x, rect.x + rect.width);
  const top = Math.min(rect.y, rect.y + rect.height);
  const bottom = Math.max(rect.y, rect.y + rect.height);
  const result: string[] = [];
  for (const note of notes) {
    if (note.x < right && note.x + note.width > left && note.y < bottom && note.y + note.height > top) {
      result.push(note.id);
    }
  }
  return result;
}

/** Clamp once for the whole group so relative timing and intervals never change. */
export function clampBatchDelta(
  notes: Pick<MidiEditorNote, "startTick" | "pitch">[],
  desiredTickDelta: number,
  desiredPitchDelta: number,
): { tickDelta: number; pitchDelta: number } {
  if (notes.length === 0) return { tickDelta: 0, pitchDelta: 0 };
  let minStart = Number.POSITIVE_INFINITY;
  let minPitch = 127;
  let maxPitch = 0;
  for (const note of notes) {
    minStart = Math.min(minStart, note.startTick);
    minPitch = Math.min(minPitch, note.pitch);
    maxPitch = Math.max(maxPitch, note.pitch);
  }
  const tickDelta = Math.max(-minStart, Math.round(desiredTickDelta));
  return {
    tickDelta: tickDelta === 0 ? 0 : tickDelta,
    pitchDelta: Math.max(-minPitch, Math.min(127 - maxPitch, Math.round(desiredPitchDelta))),
  };
}

export function createMidiClipboard(notes: MidiEditorNote[], isDrum: boolean): MidiClipboard | null {
  if (notes.length === 0) return null;
  const ordered = [...notes].sort(
    (a, b) => a.startTick - b.startTick || a.pitch - b.pitch || a.id.localeCompare(b.id),
  );
  const firstTick = ordered[0].startTick;
  return {
    sourceKind: isDrum ? "drum" : "pitched",
    notes: ordered.map((note) => ({
      pitch: note.pitch,
      relativeStartTick: note.startTick - firstTick,
      durationTick: note.durationTick,
      velocity: note.velocity,
    })),
  };
}

export function materializeClipboard(
  clipboard: MidiClipboard,
  anchorTick: number,
  channel: number,
): Array<Omit<MidiEditorNote, "id">> {
  const anchor = Math.max(0, Math.round(anchorTick));
  return clipboard.notes.map((note) => ({
    pitch: Math.max(0, Math.min(127, Math.round(note.pitch))),
    startTick: anchor + Math.max(0, Math.round(note.relativeStartTick)),
    durationTick: Math.max(1, Math.round(note.durationTick)),
    velocity: Math.max(1, Math.min(127, Math.round(note.velocity))),
    channel,
  }));
}

export function duplicateNotes(
  notes: MidiEditorNote[],
  channel: number,
): Array<Omit<MidiEditorNote, "id">> {
  if (notes.length === 0) return [];
  let start = Number.POSITIVE_INFINITY;
  let end = 0;
  for (const note of notes) {
    start = Math.min(start, note.startTick);
    end = Math.max(end, note.startTick + note.durationTick);
  }
  const offset = Math.max(1, end - start);
  return notes.map((note) => ({
    pitch: note.pitch,
    startTick: note.startTick + offset,
    durationTick: note.durationTick,
    velocity: note.velocity,
    channel,
  }));
}

export function summarizeSelectedNotes(notes: MidiEditorNote[]): SelectedNoteSummary | null {
  if (notes.length === 0) return null;
  let startTick = Number.POSITIVE_INFINITY;
  let endTick = 0;
  let minPitch = 127;
  let maxPitch = 0;
  let velocityTotal = 0;
  for (const note of notes) {
    startTick = Math.min(startTick, note.startTick);
    endTick = Math.max(endTick, note.startTick + note.durationTick);
    minPitch = Math.min(minPitch, note.pitch);
    maxPitch = Math.max(maxPitch, note.pitch);
    velocityTotal += note.velocity;
  }
  return {
    count: notes.length,
    startTick,
    endTick,
    minPitch,
    maxPitch,
    averageVelocity: Math.round(velocityTotal / notes.length),
  };
}
