// features/midi/editor/useMidiEditorDraft.test.ts（T34.4）
// Draft 状态：add/delete/move/resize/velocity、边界、轨道隔离、document reload 重置。

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

describe("useMidiEditorDraft", () => {
  it("initializes draft from document", () => {
    const { result } = renderDraft();
    expect(result.current.draftNotesByTrack.bass).toHaveLength(1);
    expect(result.current.draftNotesByTrack.bass[0].id).toBe("b1");
    expect(result.current.dirtyTracks.size).toBe(0);
  });

  it("addNote creates temp-id note and marks dirty", () => {
    const { result } = renderDraft();
    let id = "";
    act(() => {
      id = result.current.addNote("bass", { pitch: 44, startTick: 480, durationTick: 120, velocity: 90, channel: 2 });
    });
    expect(id.startsWith("draft:")).toBe(true);
    expect(result.current.draftNotesByTrack.bass).toHaveLength(2);
    expect(result.current.draftNotesByTrack.bass[1].startTick).toBe(480);
    expect(result.current.dirtyTracks.has("bass")).toBe(true);
    // melody untouched
    expect(result.current.draftNotesByTrack.melody).toHaveLength(1);
  });

  it("deleteNote removes and clears dirty only if differs", () => {
    const { result } = renderDraft();
    act(() => result.current.deleteNote("bass", "b1"));
    expect(result.current.draftNotesByTrack.bass).toHaveLength(0);
    expect(result.current.dirtyTracks.has("bass")).toBe(true);
  });

  it("moveNote changes startTick and pitch, clamps boundaries", () => {
    const { result } = renderDraft();
    act(() => result.current.moveNote("bass", "b1", -100, 200));
    expect(result.current.draftNotesByTrack.bass[0].startTick).toBe(0);
    expect(result.current.draftNotesByTrack.bass[0].pitch).toBe(127);
    act(() => result.current.moveNote("bass", "b1", 1000, -5));
    expect(result.current.draftNotesByTrack.bass[0].startTick).toBe(1000);
    expect(result.current.draftNotesByTrack.bass[0].pitch).toBe(0);
  });

  it("resizeNote changes duration and clamps to >=1", () => {
    const { result } = renderDraft();
    act(() => result.current.resizeNote("bass", "b1", -10));
    expect(result.current.draftNotesByTrack.bass[0].durationTick).toBe(1);
    act(() => result.current.resizeNote("bass", "b1", 960));
    expect(result.current.draftNotesByTrack.bass[0].durationTick).toBe(960);
    expect(result.current.draftNotesByTrack.bass[0].startTick).toBe(0); // unchanged
  });

  it("setVelocity clamps 1..127 and rounds", () => {
    const { result } = renderDraft();
    act(() => result.current.setVelocity("bass", "b1", 0));
    expect(result.current.draftNotesByTrack.bass[0].velocity).toBe(1);
    act(() => result.current.setVelocity("bass", "b1", 128));
    expect(result.current.draftNotesByTrack.bass[0].velocity).toBe(127);
    act(() => result.current.setVelocity("bass", "b1", 92.6));
    expect(result.current.draftNotesByTrack.bass[0].velocity).toBe(93);
  });

  it("updateNote applies partial patch", () => {
    const { result } = renderDraft();
    act(() => result.current.updateNote("bass", "b1", { velocity: 100 }));
    expect(result.current.draftNotesByTrack.bass[0].velocity).toBe(100);
  });

  it("bass edit does not affect melody", () => {
    const { result } = renderDraft();
    act(() => result.current.moveNote("bass", "b1", 480, 41));
    expect(result.current.draftNotesByTrack.melody[0].startTick).toBe(0);
    expect(result.current.draftNotesByTrack.melody[0].pitch).toBe(72);
  });

  it("document change (reload) resets draft", () => {
    const { result, rerender } = renderDraft(doc);
    act(() => result.current.deleteNote("bass", "b1"));
    expect(result.current.draftNotesByTrack.bass).toHaveLength(0);

    const doc2: MidiEditorDocument = {
      ...doc,
      versionId: "v5",
      tracks: [
        {
          id: "bass",
          role: "bass",
          name: "bass",
          channel: 2,
          instrument: "electric_bass_finger",
          isDrum: false,
          notes: [{ id: "b2", pitch: 41, startTick: 0, durationTick: 480, velocity: 100, channel: 2 }],
        },
        ...doc.tracks.slice(1),
      ],
    };
    rerender({ doc: doc2 });
    expect(result.current.draftNotesByTrack.bass).toHaveLength(1);
    expect(result.current.draftNotesByTrack.bass[0].id).toBe("b2");
    expect(result.current.dirtyTracks.size).toBe(0);
  });
});
