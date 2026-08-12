// features/midi/editor/useMidiEditorDraft.ts（T34.4 / T34.6）
// 编辑草稿 + 每轨道 undo/redo。
// - draftNotesByTrack：每轨道独立 session draft（immutable）
// - savedByTrack：document baseline
// - undo/redo：per-track snapshot；每个逻辑操作（含一次完整 Drag）只产生一个 undo step
// - document 变化（songId/version/reload）→ 重置 draft + history
// - editorSessionId + draftRevision：T35 stale protection；每个实际逻辑 mutation 单调 +1
// - 新增 Note 用临时 ID（draft:<uuid>），已有 Note 沿用 canonical id

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MidiEditorDocument, MidiEditorNote } from "./midiEditorTypes";

export const HISTORY_LIMIT = 80;

export interface DraftState {
  savedByTrack: Record<string, MidiEditorNote[]>;
  notesByTrack: Record<string, MidiEditorNote[]>;
  undoByTrack: Record<string, MidiEditorNote[][]>;
  redoByTrack: Record<string, MidiEditorNote[][]>;
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

function cloneNotes(notes: MidiEditorNote[]): MidiEditorNote[] {
  return notes.map((n) => ({ ...n }));
}

export interface UseMidiEditorDraftResult {
  editorSessionId: string;
  draftRevision: number;
  draftNotesByTrack: Record<string, MidiEditorNote[]>;
  dirtyTracks: Set<string>;
  canUndoTrack: (trackId: string) => boolean;
  canRedoTrack: (trackId: string) => boolean;
  addNote: (trackId: string, note: Omit<MidiEditorNote, "id">) => string;
  deleteNote: (trackId: string, noteId: string) => void;
  updateNote: (trackId: string, noteId: string, patch: Partial<Omit<MidiEditorNote, "id">>) => void;
  moveNote: (trackId: string, noteId: string, newStartTick: number, newPitch: number) => void;
  resizeNote: (trackId: string, noteId: string, newDurationTick: number) => void;
  setVelocity: (trackId: string, noteId: string, velocity: number) => void;
  insertNotes: (trackId: string, notes: Array<Omit<MidiEditorNote, "id">>) => string[];
  deleteNotes: (trackId: string, noteIds: ReadonlySet<string>) => void;
  moveNotes: (
    trackId: string,
    changes: Array<{ id: string; startTick: number; pitch: number }>,
  ) => void;
  setNotesVelocity: (trackId: string, noteIds: ReadonlySet<string>, velocity: number) => void;
  undo: (trackId: string) => void;
  redo: (trackId: string) => void;
  discardTrack: (trackId: string) => void;
  // pointerup commit：把「本操作 before」入 undo（一次拖拽=一次 undo）；由 viewport 在 drag 结束调用
  commitEdit: (trackId: string) => void;
  rebaseTo: (notes: MidiEditorNote[], trackId: string) => void;
}

export function useMidiEditorDraft(document: MidiEditorDocument | null): UseMidiEditorDraftResult {
  const [editorSessionId, setEditorSessionId] = useState(() => crypto.randomUUID());
  const [draftRevision, setDraftRevision] = useState(0);
  const draftRevisionRef = useRef(0);
  const [draftNotesByTrack, setDraftNotesByTrack] = useState<Record<string, MidiEditorNote[]>>({});
  const [savedByTrack, setSavedByTrack] = useState<Record<string, MidiEditorNote[]>>({});
  const [undoByTrack, setUndoByTrack] = useState<Record<string, MidiEditorNote[][]>>({});
  const [redoByTrack, setRedoByTrack] = useState<Record<string, MidiEditorNote[][]>>({});
  // 当前 track 是否已有「进行中操作」的 before（未 commit）→ 拖拽期间不重复入栈
  const pendingBeforeRef = useRef<Set<string>>(new Set());

  // document（songId/version）变化 → 重置 draft + history
  useEffect(() => {
    setEditorSessionId(crypto.randomUUID());
    draftRevisionRef.current = 0;
    setDraftRevision(0);
    if (!document) {
      setDraftNotesByTrack({});
      setSavedByTrack({});
      setUndoByTrack({});
      setRedoByTrack({});
      pendingBeforeRef.current = new Set();
      return;
    }
    const saved = toRecord(document.tracks);
    setSavedByTrack(saved);
    setDraftNotesByTrack(saved);
    setUndoByTrack({});
    setRedoByTrack({});
    pendingBeforeRef.current = new Set();
  }, [document]);

  const bumpDraftRevision = useCallback(() => {
    const next = draftRevisionRef.current + 1;
    draftRevisionRef.current = next;
    setDraftRevision(next);
  }, []);

  const snapshot = useCallback(
    (trackId: string): MidiEditorNote[] => cloneNotes(draftNotesByTrack[trackId] ?? savedByTrack[trackId] ?? []),
    [draftNotesByTrack, savedByTrack],
  );

  // 在变更前记录 before（若该 track 没有进行中的操作）
  const recordBefore = useCallback(
    (trackId: string) => {
      if (pendingBeforeRef.current.has(trackId)) return;
      pendingBeforeRef.current.add(trackId);
      bumpDraftRevision();
      setUndoByTrack((prev) => {
        const stack = prev[trackId] ?? [];
        const next = [...stack, snapshot(trackId)];
        if (next.length > HISTORY_LIMIT) next.shift();
        return { ...prev, [trackId]: next };
      });
      setRedoByTrack((prev) => {
        if (!(trackId in prev)) return prev;
        const next = { ...prev };
        delete next[trackId];
        return next;
      });
    },
    [bumpDraftRevision, snapshot],
  );

  const updateTrack = useCallback(
    (trackId: string, updater: (notes: MidiEditorNote[]) => MidiEditorNote[]) => {
      setDraftNotesByTrack((prev) => {
        const current = prev[trackId] ?? savedByTrack[trackId] ?? [];
        return { ...prev, [trackId]: updater(cloneNotes(current)) };
      });
    },
    [savedByTrack],
  );

  const addNote = useCallback(
    (trackId: string, note: Omit<MidiEditorNote, "id">): string => {
      recordBefore(trackId);
      const id = tempNoteId();
      updateTrack(trackId, (notes) => [...notes, { ...note, id }]);
      pendingBeforeRef.current.delete(trackId);
      return id;
    },
    [recordBefore, updateTrack],
  );

  const deleteNote = useCallback(
    (trackId: string, noteId: string) => {
      if (!snapshot(trackId).some((note) => note.id === noteId)) return;
      recordBefore(trackId);
      updateTrack(trackId, (notes) => notes.filter((n) => n.id !== noteId));
      pendingBeforeRef.current.delete(trackId);
    },
    [recordBefore, snapshot, updateTrack],
  );

  const updateNote = useCallback(
    (trackId: string, noteId: string, patch: Partial<Omit<MidiEditorNote, "id">>) => {
      const current = snapshot(trackId).find((note) => note.id === noteId);
      if (!current) return;
      const changed = Object.entries(patch).some(
        ([key, value]) => current[key as keyof MidiEditorNote] !== value,
      );
      if (!changed) return;
      recordBefore(trackId);
      updateTrack(trackId, (notes) => notes.map((n) => (n.id === noteId ? { ...n, ...patch } : n)));
      pendingBeforeRef.current.delete(trackId);
    },
    [recordBefore, snapshot, updateTrack],
  );

  const moveNote = useCallback(
    (trackId: string, noteId: string, newStartTick: number, newPitch: number) => {
      const current = snapshot(trackId).find((note) => note.id === noteId);
      const startTick = Math.max(0, newStartTick);
      const pitch = Math.max(0, Math.min(127, newPitch));
      if (!current || (current.startTick === startTick && current.pitch === pitch)) return;
      recordBefore(trackId);
      updateTrack(trackId, (notes) =>
        notes.map((n) =>
          n.id === noteId
            ? { ...n, startTick, pitch }
            : n,
        ),
      );
    },
    [recordBefore, snapshot, updateTrack],
  );

  const resizeNote = useCallback(
    (trackId: string, noteId: string, newDurationTick: number) => {
      const current = snapshot(trackId).find((note) => note.id === noteId);
      const durationTick = Math.max(1, newDurationTick);
      if (!current || current.durationTick === durationTick) return;
      recordBefore(trackId);
      updateTrack(trackId, (notes) =>
        notes.map((n) => (n.id === noteId ? { ...n, durationTick } : n)),
      );
    },
    [recordBefore, snapshot, updateTrack],
  );

  const setVelocity = useCallback(
    (trackId: string, noteId: string, velocity: number) => {
      const clamped = Math.max(1, Math.min(127, Math.round(velocity)));
      const current = snapshot(trackId).find((note) => note.id === noteId);
      if (!current || current.velocity === clamped) return;
      recordBefore(trackId);
      updateTrack(trackId, (notes) => notes.map((n) => (n.id === noteId ? { ...n, velocity: clamped } : n)));
      pendingBeforeRef.current.delete(trackId);
    },
    [recordBefore, snapshot, updateTrack],
  );

  const insertNotes = useCallback(
    (trackId: string, notes: Array<Omit<MidiEditorNote, "id">>): string[] => {
      if (notes.length === 0) return [];
      recordBefore(trackId);
      const inserted = notes.map((note) => ({ ...note, id: tempNoteId() }));
      updateTrack(trackId, (current) => [...current, ...inserted]);
      pendingBeforeRef.current.delete(trackId);
      return inserted.map((note) => note.id);
    },
    [recordBefore, updateTrack],
  );

  const deleteNotes = useCallback(
    (trackId: string, noteIds: ReadonlySet<string>) => {
      if (noteIds.size === 0) return;
      if (!snapshot(trackId).some((note) => noteIds.has(note.id))) return;
      recordBefore(trackId);
      updateTrack(trackId, (notes) => notes.filter((note) => !noteIds.has(note.id)));
      pendingBeforeRef.current.delete(trackId);
    },
    [recordBefore, snapshot, updateTrack],
  );

  const moveNotes = useCallback(
    (trackId: string, changes: Array<{ id: string; startTick: number; pitch: number }>) => {
      if (changes.length === 0) return;
      const byId = new Map(changes.map((change) => [change.id, change]));
      const changed = snapshot(trackId).some((note) => {
        const change = byId.get(note.id);
        return Boolean(
          change
          && (
            note.startTick !== Math.max(0, Math.round(change.startTick))
            || note.pitch !== Math.max(0, Math.min(127, Math.round(change.pitch)))
          )
        );
      });
      if (!changed) return;
      recordBefore(trackId);
      updateTrack(trackId, (notes) =>
        notes.map((note) => {
          const change = byId.get(note.id);
          if (!change) return note;
          return {
            ...note,
            startTick: Math.max(0, Math.round(change.startTick)),
            pitch: Math.max(0, Math.min(127, Math.round(change.pitch))),
          };
        }),
      );
    },
    [recordBefore, snapshot, updateTrack],
  );

  const setNotesVelocity = useCallback(
    (trackId: string, noteIds: ReadonlySet<string>, velocity: number) => {
      if (noteIds.size === 0) return;
      const clamped = Math.max(1, Math.min(127, Math.round(velocity)));
      if (!snapshot(trackId).some((note) => noteIds.has(note.id) && note.velocity !== clamped)) return;
      recordBefore(trackId);
      updateTrack(trackId, (notes) =>
        notes.map((note) => (noteIds.has(note.id) ? { ...note, velocity: clamped } : note)),
      );
      pendingBeforeRef.current.delete(trackId);
    },
    [recordBefore, snapshot, updateTrack],
  );

  // 拖拽结束：提交（清除 pending），使该次拖动只产生一个 undo step
  const commitEdit = useCallback((trackId: string) => {
    pendingBeforeRef.current.delete(trackId);
  }, []);

  const undo = useCallback(
    (trackId: string) => {
      if (!(undoByTrack[trackId]?.length > 0)) return;
      bumpDraftRevision();
      setUndoByTrack((prevUndo) => {
        const stack = prevUndo[trackId];
        if (!stack || stack.length === 0) return prevUndo;
        const before = stack[stack.length - 1];
        setDraftNotesByTrack((prev) => ({ ...prev, [trackId]: cloneNotes(before) }));
        setRedoByTrack((prevRedo) => ({
          ...prevRedo,
          [trackId]: [...(prevRedo[trackId] ?? []), cloneNotes(draftNotesByTrack[trackId] ?? [])],
        }));
        return { ...prevUndo, [trackId]: stack.slice(0, -1) };
      });
      pendingBeforeRef.current.delete(trackId);
    },
    [bumpDraftRevision, draftNotesByTrack, undoByTrack],
  );

  const redo = useCallback(
    (trackId: string) => {
      if (!(redoByTrack[trackId]?.length > 0)) return;
      bumpDraftRevision();
      setRedoByTrack((prevRedo) => {
        const stack = prevRedo[trackId];
        if (!stack || stack.length === 0) return prevRedo;
        const after = stack[stack.length - 1];
        setDraftNotesByTrack((prev) => ({ ...prev, [trackId]: cloneNotes(after) }));
        setUndoByTrack((prevUndo) => ({
          ...prevUndo,
          [trackId]: [...(prevUndo[trackId] ?? []), cloneNotes(draftNotesByTrack[trackId] ?? [])],
        }));
        return { ...prevRedo, [trackId]: stack.slice(0, -1) };
      });
      pendingBeforeRef.current.delete(trackId);
    },
    [bumpDraftRevision, draftNotesByTrack, redoByTrack],
  );

  const discardTrack = useCallback(
    (trackId: string) => {
      const saved = savedByTrack[trackId] ?? [];
      if (notesDirty(saved, snapshot(trackId))) bumpDraftRevision();
      setDraftNotesByTrack((prev) => ({ ...prev, [trackId]: cloneNotes(saved) }));
      setUndoByTrack((prev) => {
        const next = { ...prev };
        delete next[trackId];
        return next;
      });
      setRedoByTrack((prev) => {
        const next = { ...prev };
        delete next[trackId];
        return next;
      });
      pendingBeforeRef.current.delete(trackId);
    },
    [bumpDraftRevision, savedByTrack, snapshot],
  );

  // Save 后：用后端返回的 canonical notes rebase 当前轨道（清除 history / pending）
  const rebaseTo = useCallback((notes: MidiEditorNote[], trackId: string) => {
    const canonical = cloneNotes(notes);
    const current = draftNotesByTrack[trackId] ?? savedByTrack[trackId] ?? [];
    const saved = savedByTrack[trackId] ?? [];
    if (notesDirty(current, canonical) || notesDirty(saved, canonical)) bumpDraftRevision();
    setSavedByTrack((prev) => ({ ...prev, [trackId]: canonical }));
    setDraftNotesByTrack((prev) => ({ ...prev, [trackId]: canonical }));
    setUndoByTrack((prev) => {
      const next = { ...prev };
      delete next[trackId];
      return next;
    });
    setRedoByTrack((prev) => {
      const next = { ...prev };
      delete next[trackId];
      return next;
    });
    pendingBeforeRef.current.delete(trackId);
  }, [bumpDraftRevision, draftNotesByTrack, savedByTrack]);

  const dirtyTracks = useMemo(() => {
    const dirty = new Set<string>();
    for (const trackId of Object.keys(draftNotesByTrack)) {
      const saved = savedByTrack[trackId] ?? [];
      const trackDraft = draftNotesByTrack[trackId] ?? [];
      if (notesDirty(saved, trackDraft)) dirty.add(trackId);
    }
    return dirty;
  }, [draftNotesByTrack, savedByTrack]);

  const canUndoTrack = useCallback(
    (trackId: string) => (undoByTrack[trackId]?.length ?? 0) > 0,
    [undoByTrack],
  );
  const canRedoTrack = useCallback(
    (trackId: string) => (redoByTrack[trackId]?.length ?? 0) > 0,
    [redoByTrack],
  );

  return {
    editorSessionId,
    draftRevision,
    draftNotesByTrack,
    dirtyTracks,
    canUndoTrack,
    canRedoTrack,
    addNote,
    deleteNote,
    updateNote,
    moveNote,
    resizeNote,
    setVelocity,
    insertNotes,
    deleteNotes,
    moveNotes,
    setNotesVelocity,
    undo,
    redo,
    discardTrack,
    commitEdit,
    rebaseTo,
  };
}
