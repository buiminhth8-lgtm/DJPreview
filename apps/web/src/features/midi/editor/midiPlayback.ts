// T34.7 transport 纯函数：Draft 选择、tick timing、loop validation。

import type { MidiEditorDocument, MidiEditorNote } from "./midiEditorTypes";
import type { MidiPreviewScope } from "./midiEditorApi";

export interface MidiPreviewTrackSnapshot {
  trackId: string;
  notes: MidiEditorNote[];
}

function notesForTrack(
  trackId: string,
  saved: MidiEditorNote[],
  draftNotesByTrack: Record<string, MidiEditorNote[]>,
): MidiEditorNote[] {
  return Object.prototype.hasOwnProperty.call(draftNotesByTrack, trackId)
    ? draftNotesByTrack[trackId]
    : saved;
}

/** Current = selected draft/saved；All = 每轨各自 draft/saved。 */
export function buildMidiPreviewTracks(
  document: MidiEditorDocument,
  draftNotesByTrack: Record<string, MidiEditorNote[]>,
  selectedTrackId: string | null,
  scope: MidiPreviewScope,
): MidiPreviewTrackSnapshot[] {
  if (scope === "current_track") {
    const track = document.tracks.find((candidate) => candidate.id === selectedTrackId);
    return track
      ? [{ trackId: track.id, notes: notesForTrack(track.id, track.notes, draftNotesByTrack) }]
      : [];
  }
  return document.tracks.map((track) => ({
    trackId: track.id,
    notes: notesForTrack(track.id, track.notes, draftNotesByTrack),
  }));
}

export function previewEndTick(tracks: MidiPreviewTrackSnapshot[]): number {
  let end = 0;
  for (const track of tracks) {
    for (const note of track.notes) {
      end = Math.max(end, note.startTick + note.durationTick);
    }
  }
  return end;
}

export function tickToSeconds(tick: number, ppq: number, bpm: number): number {
  if (ppq <= 0 || bpm <= 0) return 0;
  return (Math.max(0, tick) / ppq) * (60 / bpm);
}

export function secondsToTick(seconds: number, ppq: number, bpm: number): number {
  if (ppq <= 0 || bpm <= 0) return 0;
  return Math.max(0, Math.round(seconds * (bpm / 60) * ppq));
}

export function clampPlaybackTick(tick: number, endTick: number): number {
  return Math.max(0, Math.min(Math.max(0, endTick), Math.round(tick)));
}

export function isValidLoop(startTick: number, endTick: number, maxTick?: number): boolean {
  if (!Number.isFinite(startTick) || !Number.isFinite(endTick)) return false;
  if (startTick < 0 || endTick <= startTick) return false;
  return maxTick == null || endTick <= maxTick;
}
