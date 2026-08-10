// features/midi/editor/useMidiEditorDraft.history.test.ts（T34.6）
// Undo/Redo、dirty 语义、commit-on-pointerup（一次拖拽=一次 undo）、discard、rebase。

import { describe, expect, it } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { useMidiEditorDraft } from "./useMidiEditorDraft";
import type { MidiEditorDocument } from "./midiEditorTypes";

const doc: MidiEditorDocument = {
  songId: "s1",
  versionId: "v4",
  ppq: 480,
  bpm: 120,
  timeSignature: [4, 4],
  totalBars: 8,
  tracks: [
    {
      id: "bass",
      role: "bass",
      name: "bass",
      channel: 2,
      instrument: "electric_bass_finger",
      isDrum: false,
      notes: [{ id: "b1", pitch: 40, startTick: 0, durationTick: 480, velocity: 110, channel: 2 }],
    },
    {
      id: "melody",
      role: "melody",
      name: "melody",
      channel: 0,
      instrument: null,
      isDrum: false,
      notes: [{ id: "m1", pitch: 72, startTick: 0, durationTick: 480, velocity: 100, channel: 0 }],
    },
  ],
};

function renderDraft(document: MidiEditorDocument | null = doc) {
  return renderHook(({ doc: d }) => useMidiEditorDraft(d), { initialProps: { doc: document } });
}

describe("useMidiEditorDraft history", () => {
  it("add → undo → redo round trip", () => {
    const { result } = renderDraft();
    act(() => result.current.addNote("bass", { pitch: 44, startTick: 480, durationTick: 120, velocity: 90, channel: 2 }));
    expect(result.current.draftNotesByTrack.bass).toHaveLength(2);
    expect(result.current.dirtyTracks.has("bass")).toBe(true);
    act(() => result.current.undo("bass"));
    expect(result.current.draftNotesByTrack.bass).toHaveLength(1);
    act(() => result.current.redo("bass"));
    expect(result.current.draftNotesByTrack.bass).toHaveLength(2);
  });

  it("one drag (multiple moveNote + commitEdit) = one undo", () => {
    const { result } = renderDraft();
    // simulate drag: many pointermoves then commitEdit on pointerup
    act(() => result.current.moveNote("bass", "b1", 120, 41));
    act(() => result.current.moveNote("bass", "b1", 240, 42));
    act(() => result.current.moveNote("bass", "b1", 360, 43));
    act(() => result.current.commitEdit("bass"));
    expect(result.current.draftNotesByTrack.bass[0].startTick).toBe(360);
    expect(result.current.draftNotesByTrack.bass[0].pitch).toBe(43);
    // one undo → back to original
    act(() => result.current.undo("bass"));
    expect(result.current.draftNotesByTrack.bass[0]).toMatchObject({ startTick: 0, pitch: 40 });
  });

  it("undo back to baseline → dirty false; redo → dirty true", () => {
    const { result } = renderDraft();
    act(() => result.current.setVelocity("bass", "b1", 60));
    expect(result.current.dirtyTracks.has("bass")).toBe(true);
    act(() => result.current.undo("bass"));
    expect(result.current.dirtyTracks.size).toBe(0);
    act(() => result.current.redo("bass"));
    expect(result.current.dirtyTracks.has("bass")).toBe(true);
  });

  it("delete → undo restores", () => {
    const { result } = renderDraft();
    act(() => result.current.deleteNote("bass", "b1"));
    expect(result.current.draftNotesByTrack.bass).toHaveLength(0);
    act(() => result.current.undo("bass"));
    expect(result.current.draftNotesByTrack.bass).toHaveLength(1);
    expect(result.current.draftNotesByTrack.bass[0].id).toBe("b1");
  });

  it("history is per-track (bass undo does not touch melody)", () => {
    const { result } = renderDraft();
    act(() => result.current.moveNote("bass", "b1", 960, 41));
    act(() => result.current.moveNote("melody", "m1", 240, 74));
    act(() => result.current.undo("bass"));
    // melody unchanged by bass undo
    expect(result.current.draftNotesByTrack.melody[0]).toMatchObject({ startTick: 240, pitch: 74 });
    // bass back to original
    expect(result.current.draftNotesByTrack.bass[0]).toMatchObject({ startTick: 0, pitch: 40 });
  });

  it("discardTrack resets to saved and clears history/dirty", () => {
    const { result } = renderDraft();
    act(() => result.current.addNote("bass", { pitch: 44, startTick: 480, durationTick: 120, velocity: 90, channel: 2 }));
    act(() => result.current.setVelocity("bass", "b1", 50));
    act(() => result.current.discardTrack("bass"));
    expect(result.current.draftNotesByTrack.bass).toHaveLength(1);
    expect(result.current.draftNotesByTrack.bass[0].velocity).toBe(110);
    expect(result.current.dirtyTracks.size).toBe(0);
    expect(result.current.canUndoTrack("bass")).toBe(false);
  });

  it("rebaseTo replaces draft with canonical notes and clears dirty/history", () => {
    const { result } = renderDraft();
    act(() => result.current.addNote("bass", { pitch: 44, startTick: 480, durationTick: 120, velocity: 90, channel: 2 }));
    act(() => result.current.rebaseTo([{ id: "b1", pitch: 40, startTick: 0, durationTick: 480, velocity: 110, channel: 2 }], "bass"));
    expect(result.current.draftNotesByTrack.bass).toHaveLength(1);
    expect(result.current.draftNotesByTrack.bass[0].id).toBe("b1");
    expect(result.current.dirtyTracks.size).toBe(0);
    expect(result.current.canUndoTrack("bass")).toBe(false);
    expect(result.current.canRedoTrack("bass")).toBe(false);
  });

  it("document change resets draft and history", () => {
    const { result, rerender } = renderDraft(doc);
    act(() => result.current.addNote("bass", { pitch: 44, startTick: 480, durationTick: 120, velocity: 90, channel: 2 }));
    const doc2: MidiEditorDocument = { ...doc, versionId: "v5" };
    rerender({ doc: doc2 });
    expect(result.current.draftNotesByTrack.bass).toHaveLength(1);
    expect(result.current.draftNotesByTrack.bass[0].id).toBe("b1");
    expect(result.current.dirtyTracks.size).toBe(0);
    expect(result.current.canUndoTrack("bass")).toBe(false);
  });

  it("canUndo/canRedo reflect stack", () => {
    const { result } = renderDraft();
    expect(result.current.canUndoTrack("bass")).toBe(false);
    expect(result.current.canRedoTrack("bass")).toBe(false);
    act(() => result.current.moveNote("bass", "b1", 480, 41));
    expect(result.current.canUndoTrack("bass")).toBe(true);
    act(() => result.current.undo("bass"));
    expect(result.current.canUndoTrack("bass")).toBe(false);
    expect(result.current.canRedoTrack("bass")).toBe(true);
  });

  it("batch insert/delete/velocity each create one undo step", () => {
    const { result } = renderDraft();
    let ids: string[] = [];
    act(() => {
      ids = result.current.insertNotes("bass", [
        { pitch: 42, startTick: 480, durationTick: 120, velocity: 80, channel: 2 },
        { pitch: 45, startTick: 720, durationTick: 120, velocity: 90, channel: 2 },
      ]);
    });
    expect(ids).toHaveLength(2);
    expect(new Set(ids).size).toBe(2);
    expect(ids.every((id) => id.startsWith("draft:"))).toBe(true);
    act(() => result.current.undo("bass"));
    expect(result.current.draftNotesByTrack.bass).toHaveLength(1);
    act(() => result.current.redo("bass"));
    expect(result.current.draftNotesByTrack.bass).toHaveLength(3);

    act(() => result.current.deleteNotes("bass", new Set(ids)));
    expect(result.current.draftNotesByTrack.bass).toHaveLength(1);
    act(() => result.current.undo("bass"));
    expect(result.current.draftNotesByTrack.bass).toHaveLength(3);

    act(() => result.current.setNotesVelocity("bass", new Set(["b1", ...ids]), 55));
    expect(result.current.draftNotesByTrack.bass.every((note) => note.velocity === 55)).toBe(true);
    act(() => result.current.undo("bass"));
    expect(result.current.draftNotesByTrack.bass.map((note) => note.velocity)).toEqual([110, 80, 90]);
  });

  it("batch drag updates selected notes in one scan and one undo step", () => {
    const { result } = renderDraft();
    let insertedId = "";
    act(() => {
      insertedId = result.current.insertNotes("bass", [
        { pitch: 44, startTick: 240, durationTick: 120, velocity: 90, channel: 2 },
      ])[0];
    });
    act(() => result.current.moveNotes("bass", [
      { id: "b1", startTick: 480, pitch: 41 },
      { id: insertedId, startTick: 720, pitch: 45 },
    ]));
    act(() => result.current.moveNotes("bass", [
      { id: "b1", startTick: 960, pitch: 42 },
      { id: insertedId, startTick: 1200, pitch: 46 },
    ]));
    act(() => result.current.commitEdit("bass"));
    expect(result.current.draftNotesByTrack.bass.map((note) => [note.startTick, note.pitch])).toEqual([
      [960, 42],
      [1200, 46],
    ]);
    act(() => result.current.undo("bass"));
    expect(result.current.draftNotesByTrack.bass.map((note) => [note.startTick, note.pitch])).toEqual([
      [0, 40],
      [240, 44],
    ]);
  });

  it("handles 500-note insert, move and delete batches", () => {
    const { result } = renderDraft();
    const batch = Array.from({ length: 500 }, (_, index) => ({
      pitch: 36 + (index % 48),
      startTick: 480 + index * 30,
      durationTick: 30,
      velocity: 90,
      channel: 2,
    }));
    let ids: string[] = [];
    act(() => {
      ids = result.current.insertNotes("bass", batch);
    });
    expect(result.current.draftNotesByTrack.bass).toHaveLength(501);
    act(() => result.current.moveNotes(
      "bass",
      ids.map((id, index) => ({ id, startTick: 960 + index * 30, pitch: 37 + (index % 48) })),
    ));
    act(() => result.current.commitEdit("bass"));
    expect(result.current.draftNotesByTrack.bass[1]).toMatchObject({ startTick: 960, pitch: 37 });
    act(() => result.current.deleteNotes("bass", new Set(ids)));
    expect(result.current.draftNotesByTrack.bass).toHaveLength(1);
    act(() => result.current.undo("bass"));
    expect(result.current.draftNotesByTrack.bass).toHaveLength(501);
  });
});
