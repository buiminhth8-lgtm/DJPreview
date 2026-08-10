// features/midi/editor/useMidiEditorDraft.ts（T34.4）
// 编辑草稿：draftNotesByTrackId。
// - 每条轨道独立保留当前 session draft
// - 编辑只改 draft，不触碰 document / savedNotes / backend
// - document 变化（songId/version/reload）→ 重置 draft
// - 新增 Note 使用临时 ID（draft:<uuid>），已有 Note 沿用 canonical id

import { useCallback, useEffect, useRef, useState } from "react";
import type { MidiEditorDocument, MidiEditorNote } from "./midiEditorTypes";

export interface DraftState {
  savedByTrack: Record<string, MidiEditorNote[]>;
  notesByTrack: Record<string, MidiEditorNote[]>;
}

export function tempNoteId(): string {
  return `draft:${crypto.randomUUID()}`;
}

export function notesDirty(saved: MidiEditorNote[], draft: MidiEditorNote[]): boolean {
  if (saved.length !== draft.length) return true;
  for (let i = 0; i < saved.length; i += 1) {
    const a = saved[i];
    const b = draft[i];
    if (
      a.id !== b.id ||
      a.pitch !== b.pitch ||
      a.startTick !== b.startTick ||
      a.durationTick !== b.durationTick ||
      a.velocity !== b.velocity ||
      a.channel !== b.channel
    ) {
      return true;
    }
  }
  return false;
}

function toRecord(tracks: MidiEditorDocument["tracks"]): Record<string, MidiEditorNote[]> {
  const rec: Record<string, MidiEditorNote[]> = {};
  for (const t of tracks) rec[t.id] = t.notes.map((n) => ({ ...n }));
  return rec;
}

export interface UseMidiEditorDraftResult {
  draftNotesByTrack: Record<string, MidiEditorNote[]>;
  dirtyTracks: Set<string>;
  addNote: (trackId: string, note: Omit<MidiEditorNote, "id">) => string;
  deleteNote: (trackId: string, noteId: string) => void;
  updateNote: (trackId: string, noteId: string, patch: Partial<Omit<MidiEditorNote, "id">>) => void;
  moveNote: (
    trackId: string,
    noteId: string,
    newStartTick: number,
    newPitch: number,
  ) => void;
  resizeNote: (trackId: string, noteId: string, newDurationTick: number) => void;
  setVelocity: (trackId: string, noteId: string, velocity: number) => void;
}

export function useMidiEditorDraft(document: MidiEditorDocument | null): UseMidiEditorDraftResult {
  const [draftNotesByTrack, setDraftNotesByTrack] = useState<Record<string, MidiEditorNote[]>>({});
  const [savedByTrack, setSavedByTrack] = useState<Record<string, MidiEditorNote[]>>({});
  const inFlightRef = useRef(false);

  // document（songId/version）变化 → 重置 draft 为 saved
  useEffect(() => {
    if (!document) {
      setDraftNotesByTrack({});
      setSavedByTrack({});
      return;
    }
    const saved = toRecord(document.tracks);
    setSavedByTrack(saved);
    setDraftNotesByTrack(saved);
  }, [document]);

  const updateTrack = useCallback(
    (trackId: string, updater: (notes: MidiEditorNote[]) => MidiEditorNote[]) => {
      inFlightRef.current = true;
      setDraftNotesByTrack((prev) => {
        const current = prev[trackId] ?? savedByTrack[trackId] ?? [];
        return { ...prev, [trackId]: updater(current.map((n) => ({ ...n }))) };
      });
      inFlightRef.current = false;
    },
    [savedByTrack],
  );

  const addNote = useCallback(
    (trackId: string, note: Omit<MidiEditorNote, "id">): string => {
      const id = tempNoteId();
      updateTrack(trackId, (notes) => [...notes, { ...note, id }]);
      return id;
    },
    [updateTrack],
  );

  const deleteNote = useCallback(
    (trackId: string, noteId: string) => {
      updateTrack(trackId, (notes) => notes.filter((n) => n.id !== noteId));
    },
    [updateTrack],
  );

  const updateNote = useCallback(
    (trackId: string, noteId: string, patch: Partial<Omit<MidiEditorNote, "id">>) => {
      updateTrack(trackId, (notes) =>
        notes.map((n) => (n.id === noteId ? { ...n, ...patch } : n)),
      );
    },
    [updateTrack],
  );

  const moveNote = useCallback(
    (trackId: string, noteId: string, newStartTick: number, newPitch: number) => {
      updateTrack(trackId, (notes) =>
        notes.map((n) =>
          n.id === noteId ? { ...n, startTick: Math.max(0, newStartTick), pitch: Math.max(0, Math.min(127, newPitch)) } : n,
        ),
      );
    },
    [updateTrack],
  );

  const resizeNote = useCallback(
    (trackId: string, noteId: string, newDurationTick: number) => {
      updateTrack(trackId, (notes) =>
        notes.map((n) =>
          n.id === noteId ? { ...n, durationTick: Math.max(1, newDurationTick) } : n,
        ),
      );
    },
    [updateTrack],
  );

  const setVelocity = useCallback(
    (trackId: string, noteId: string, velocity: number) => {
      const clamped = Math.max(1, Math.min(127, Math.round(velocity)));
      updateTrack(trackId, (notes) =>
        notes.map((n) => (n.id === noteId ? { ...n, velocity: clamped } : n)),
      );
    },
    [updateTrack],
  );

  const dirtyTracks = new Set<string>();
  for (const trackId of Object.keys(draftNotesByTrack)) {
    const saved = savedByTrack[trackId] ?? [];
    const draft = draftNotesByTrack[trackId] ?? [];
    if (notesDirty(saved, draft)) dirtyTracks.add(trackId);
  }

  return { draftNotesByTrack, dirtyTracks, addNote, deleteNote, updateNote, moveNote, resizeNote, setVelocity };
}
