import { describe, expect, it } from "vitest";

import {
  applySelection,
  clampBatchDelta,
  createMidiClipboard,
  duplicateNotes,
  intersectingNoteIds,
  materializeClipboard,
  summarizeSelectedNotes,
} from "./midiSelection";
import type { MidiEditorNote } from "./midiEditorTypes";

const notes: MidiEditorNote[] = [
  { id: "a", pitch: 60, startTick: 120, durationTick: 120, velocity: 80, channel: 0 },
  { id: "b", pitch: 64, startTick: 360, durationTick: 240, velocity: 100, channel: 0 },
];

describe("midi selection model", () => {
  it("supports replace, append, toggle and clear", () => {
    expect([...applySelection(new Set(["old"]), ["a"], "replace")]).toEqual(["a"]);
    expect([...applySelection(new Set(["a"]), ["b"], "append")]).toEqual(["a", "b"]);
    expect([...applySelection(new Set(["a", "b"]), ["a", "x"], "toggle")]).toEqual(["b", "x"]);
    expect(applySelection(new Set(["a"]), [], "replace").size).toBe(0);
  });

  it("box intersection works in content coordinates", () => {
    const hit = intersectingNoteIds(
      [
        { id: "a", x: 100, y: 40, width: 40, height: 12 },
        { id: "b", x: 400, y: 100, width: 40, height: 12 },
      ],
      { x: 90, y: 30, width: 80, height: 40 },
    );
    expect(hit).toEqual(["a"]);
  });

  it("clamps a whole group with one uniform delta", () => {
    expect(clampBatchDelta(notes, -999, 100)).toEqual({ tickDelta: -120, pitchDelta: 63 });
    const delta = clampBatchDelta(notes, 240, -100);
    expect(delta).toEqual({ tickDelta: 240, pitchDelta: -60 });
    expect(notes.map((note) => note.startTick + delta.tickDelta)).toEqual([360, 600]);
  });

  it("copies relative structure and pastes on the target channel without ids", () => {
    const clipboard = createMidiClipboard(notes, false)!;
    expect(clipboard).toEqual({
      sourceKind: "pitched",
      notes: [
        { pitch: 60, relativeStartTick: 0, durationTick: 120, velocity: 80 },
        { pitch: 64, relativeStartTick: 240, durationTick: 240, velocity: 100 },
      ],
    });
    expect(materializeClipboard(clipboard, 960, 3)).toEqual([
      { pitch: 60, startTick: 960, durationTick: 120, velocity: 80, channel: 3 },
      { pitch: 64, startTick: 1200, durationTick: 240, velocity: 100, channel: 3 },
    ]);
  });

  it("duplicates by the full selection time span and summarizes inspector data", () => {
    expect(duplicateNotes(notes, 2).map((note) => note.startTick)).toEqual([600, 840]);
    expect(summarizeSelectedNotes(notes)).toEqual({
      count: 2,
      startTick: 120,
      endTick: 600,
      minPitch: 60,
      maxPitch: 64,
      averageVelocity: 90,
    });
  });

  it("handles 100 and 500 selected notes in linear passes", () => {
    for (const count of [100, 500]) {
      const many = Array.from({ length: count }, (_, index) => ({
        id: `n${index}`,
        pitch: index % 128,
        startTick: index * 30,
        durationTick: 30,
        velocity: 90,
        channel: 0,
      }));
      const clipboard = createMidiClipboard(many, false)!;
      expect(clipboard.notes).toHaveLength(count);
      expect(materializeClipboard(clipboard, 480, 5)).toHaveLength(count);
      expect(summarizeSelectedNotes(many)?.count).toBe(count);
      expect(clampBatchDelta(many, -999, 999)).toEqual({
        tickDelta: 0,
        pitchDelta: 127 - Math.min(127, count - 1),
      });
    }
  });
});
