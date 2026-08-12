import { useLayoutEffect, useMemo, useRef, useState } from "react";

import type { MidiEditorNote } from "../midiEditorTypes";
import type { CapturedMidiEditScope, MidiEditScope } from "./aiMidiEditTypes";

function validateTickRange(startTick: number, endTick: number): void {
  if (!Number.isInteger(startTick) || !Number.isInteger(endTick) || startTick < 0 || endTick <= startTick) {
    throw new Error("MIDI edit scope requires 0 <= startTick < endTick");
  }
}

export function normalizeMidiEditScope(scope: MidiEditScope): MidiEditScope {
  const trackId = scope.trackId.trim();
  if (!trackId) throw new Error("MIDI edit scope requires trackId");
  switch (scope.type) {
    case "selected_notes": {
      const noteIds = [...scope.noteIds].map((id) => id.trim()).sort();
      if (!noteIds.length || noteIds.some((id) => !id) || new Set(noteIds).size !== noteIds.length) {
        throw new Error("selected_notes requires unique, non-empty noteIds");
      }
      return { type: scope.type, trackId, noteIds };
    }
    case "track":
      return { type: scope.type, trackId };
    case "section": {
      validateTickRange(scope.startTick, scope.endTick);
      const sectionId = scope.sectionId.trim();
      if (!sectionId) throw new Error("section scope requires sectionId");
      return {
        type: scope.type,
        trackId,
        sectionId,
        startTick: scope.startTick,
        endTick: scope.endTick,
      };
    }
    case "tick_range":
      validateTickRange(scope.startTick, scope.endTick);
      return {
        type: scope.type,
        trackId,
        startTick: scope.startTick,
        endTick: scope.endTick,
      };
  }
}

export function canonicalMidiEditScopeJson(scope: MidiEditScope): string {
  return JSON.stringify(normalizeMidiEditScope(scope));
}

export async function midiEditScopeFingerprint(scope: MidiEditScope): Promise<string> {
  const bytes = new TextEncoder().encode(canonicalMidiEditScopeJson(scope));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function canonicalNoteOrder(a: MidiEditorNote, b: MidiEditorNote): number {
  return (
    a.startTick - b.startTick
    || a.pitch - b.pitch
    || a.channel - b.channel
    || a.id.localeCompare(b.id)
  );
}

export function captureMidiEditScope(
  scope: MidiEditScope,
  trackNotes: readonly MidiEditorNote[],
): CapturedMidiEditScope {
  const normalized = normalizeMidiEditScope(scope);
  const byId = new Map(trackNotes.map((note) => [note.id, note]));
  if (byId.size !== trackNotes.length) throw new Error("track notes contain duplicate IDs");

  let notes: MidiEditorNote[];
  if (normalized.type === "selected_notes") {
    notes = normalized.noteIds.map((id) => {
      const note = byId.get(id);
      if (!note) throw new Error("selected note not found: " + id);
      return note;
    });
  } else if (normalized.type === "track") {
    notes = [...trackNotes];
  } else {
    notes = trackNotes.filter(
      (note) => note.startTick >= normalized.startTick && note.startTick < normalized.endTick,
    );
  }
  return {
    scope: normalized,
    notes: notes.map((note) => ({ ...note })).sort(canonicalNoteOrder),
  };
}

export function defaultMidiEditScope(
  trackId: string,
  selectedNoteIds: ReadonlySet<string>,
): MidiEditScope {
  if (selectedNoteIds.size > 0) {
    return { type: "selected_notes", trackId, noteIds: [...selectedNoteIds] };
  }
  return { type: "track", trackId };
}

/** Session-local monotonic scope identity; away-and-back still invalidates old work. */
export function useMidiEditScopeRevision(
  editorSessionId: string,
  scope: MidiEditScope | null,
): number {
  const signature = useMemo(
    () => (scope ? canonicalMidiEditScopeJson(scope) : ""),
    [scope],
  );
  const sessionRef = useRef(editorSessionId);
  const signatureRef = useRef(signature);
  const [revision, setRevision] = useState(0);

  useLayoutEffect(() => {
    if (sessionRef.current !== editorSessionId) {
      sessionRef.current = editorSessionId;
      signatureRef.current = signature;
      setRevision(0);
      return;
    }
    if (signatureRef.current !== signature) {
      signatureRef.current = signature;
      setRevision((value) => value + 1);
    }
  }, [editorSessionId, signature]);

  return revision;
}
