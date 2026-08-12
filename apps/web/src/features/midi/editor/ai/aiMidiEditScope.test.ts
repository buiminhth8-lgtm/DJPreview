import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  canonicalMidiEditScopeJson,
  captureMidiEditScope,
  defaultMidiEditScope,
  midiEditScopeFingerprint,
  normalizeMidiEditScope,
  useMidiEditScopeRevision,
} from "./aiMidiEditScope";
import type { MidiEditScope } from "./aiMidiEditTypes";
import type { MidiEditorNote } from "../midiEditorTypes";

const notes: MidiEditorNote[] = [
  { id: "b2", pitch: 42, startTick: 480, durationTick: 120, velocity: 80, channel: 2 },
  { id: "b1", pitch: 40, startTick: 0, durationTick: 240, velocity: 90, channel: 2 },
  { id: "b3", pitch: 44, startTick: 960, durationTick: 120, velocity: 100, channel: 2 },
];

describe("AI MIDI edit scope", () => {
  it("normalizes selected IDs and matches the frozen Python fingerprint", async () => {
    const scope: MidiEditScope = {
      type: "selected_notes",
      trackId: "bass",
      noteIds: ["b2", "b1"],
    };
    expect(canonicalMidiEditScopeJson(scope)).toBe(
      '{"type":"selected_notes","trackId":"bass","noteIds":["b1","b2"]}',
    );
    await expect(midiEditScopeFingerprint(scope)).resolves.toBe(
      "ac22ebf675cca80ab382b8cb347d0d8e57127ff9052eaf121ba55fe1bb59df66",
    );
  });

  it.each([
    [
      { type: "track", trackId: "bass" } as MidiEditScope,
      '{"type":"track","trackId":"bass"}',
      "95713958c4a25ceb8c2b000c2f8ac314575024dd08415f59cf5bb09ddaddb41d",
    ],
    [
      {
        type: "section",
        trackId: "bass",
        sectionId: "chorus",
        startTick: 3840,
        endTick: 7680,
      } as MidiEditScope,
      '{"type":"section","trackId":"bass","sectionId":"chorus","startTick":3840,"endTick":7680}',
      "4689cd3055240c5f7234784fb7f9d3a2a0fce645af842e1ae31b027f1d8fb712",
    ],
    [
      {
        type: "tick_range",
        trackId: "bass",
        startTick: 480,
        endTick: 960,
      } as MidiEditScope,
      '{"type":"tick_range","trackId":"bass","startTick":480,"endTick":960}',
      "289f97cdc91aeacb3613350cf8d5904f6b036c77ea328f358d46c865ce48f536",
    ],
  ])("matches Python canonical fixture %#", async (scope, canonical, fingerprint) => {
    expect(canonicalMidiEditScopeJson(scope)).toBe(canonical);
    await expect(midiEditScopeFingerprint(scope)).resolves.toBe(fingerprint);
  });

  it("captures selected, track and half-open tick scopes from current Draft", () => {
    expect(captureMidiEditScope(
      { type: "selected_notes", trackId: "bass", noteIds: ["b2", "b1"] },
      notes,
    ).notes.map((note) => note.id)).toEqual(["b1", "b2"]);
    expect(captureMidiEditScope({ type: "track", trackId: "bass" }, notes).notes).toHaveLength(3);
    expect(captureMidiEditScope(
      { type: "tick_range", trackId: "bass", startTick: 0, endTick: 960 },
      notes,
    ).notes.map((note) => note.id)).toEqual(["b1", "b2"]);
  });

  it("rejects invalid ranges, duplicate IDs and missing selected Notes", () => {
    expect(() => normalizeMidiEditScope({
      type: "tick_range",
      trackId: "bass",
      startTick: 960,
      endTick: 960,
    })).toThrow();
    expect(() => normalizeMidiEditScope({
      type: "selected_notes",
      trackId: "bass",
      noteIds: ["b1", "b1"],
    })).toThrow();
    expect(() => captureMidiEditScope({
      type: "selected_notes",
      trackId: "bass",
      noteIds: ["missing"],
    }, notes)).toThrow("selected note not found");
  });

  it("defaults to selected_notes when selection exists and track otherwise", () => {
    expect(defaultMidiEditScope("bass", new Set(["b2", "b1"]))).toEqual({
      type: "selected_notes",
      trackId: "bass",
      noteIds: ["b2", "b1"],
    });
    expect(defaultMidiEditScope("bass", new Set())).toEqual({
      type: "track",
      trackId: "bass",
    });
  });

  it("scopeRevision increments on every scope change and resets for a new editor session", () => {
    const trackScope: MidiEditScope = { type: "track", trackId: "bass" };
    const selectedScope: MidiEditScope = {
      type: "selected_notes",
      trackId: "bass",
      noteIds: ["b1"],
    };
    const { result, rerender } = renderHook(
      ({ session, scope }) => useMidiEditScopeRevision(session, scope),
      { initialProps: { session: "session-a", scope: trackScope as MidiEditScope | null } },
    );
    expect(result.current).toBe(0);
    act(() => rerender({ session: "session-a", scope: selectedScope }));
    expect(result.current).toBe(1);
    act(() => rerender({ session: "session-a", scope: trackScope }));
    expect(result.current).toBe(2);
    act(() => rerender({ session: "session-b", scope: trackScope }));
    expect(result.current).toBe(0);
  });
});
