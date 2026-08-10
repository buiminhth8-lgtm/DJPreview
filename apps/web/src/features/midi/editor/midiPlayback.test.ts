import { describe, expect, it } from "vitest";

import type { MidiEditorDocument, MidiEditorNote } from "./midiEditorTypes";
import {
  buildMidiPreviewTracks,
  isValidLoop,
  previewEndTick,
  secondsToTick,
  tickToSeconds,
} from "./midiPlayback";

const note = (id: string, pitch: number, startTick = 0): MidiEditorNote => ({
  id,
  pitch,
  startTick,
  durationTick: 480,
  velocity: 100,
  channel: pitch < 60 ? 2 : 0,
});

const document: MidiEditorDocument = {
  songId: "song-1",
  versionId: "v4",
  ppq: 480,
  bpm: 120,
  timeSignature: [4, 4],
  totalBars: 8,
  tracks: [
    { id: "melody", role: "melody", name: "melody", channel: 0, instrument: null, isDrum: false, notes: [note("m1", 72)] },
    { id: "bass", role: "bass", name: "bass", channel: 2, instrument: null, isDrum: false, notes: [note("b1", 40)] },
  ],
};

describe("MIDI preview snapshot", () => {
  it("Current Track uses the selected unsaved draft only", () => {
    const bassDraft = [note("b1", 45, 480)];
    const tracks = buildMidiPreviewTracks(document, { bass: bassDraft }, "bass", "current_track");
    expect(tracks).toEqual([{ trackId: "bass", notes: bassDraft }]);
  });

  it("an empty draft replaces saved notes instead of falling back", () => {
    const tracks = buildMidiPreviewTracks(document, { bass: [] }, "bass", "current_track");
    expect(tracks).toEqual([{ trackId: "bass", notes: [] }]);
  });

  it("All Tracks merges each draft with untouched saved tracks", () => {
    const bassDraft = [note("draft", 47)];
    const tracks = buildMidiPreviewTracks(document, { bass: bassDraft }, "bass", "all_tracks");
    expect(tracks.map((track) => track.trackId)).toEqual(["melody", "bass"]);
    expect(tracks[0].notes).toBe(document.tracks[0].notes);
    expect(tracks[1].notes).toBe(bassDraft);
  });

  it.each([500, 1000, 3000])("builds a %i-note snapshot without per-note timers", (count) => {
    const notes = Array.from({ length: count }, (_, index) => note(`n-${index}`, 40 + (index % 12), index * 30));
    const started = performance.now();
    const tracks = buildMidiPreviewTracks(document, { bass: notes }, "bass", "current_track");
    const elapsed = performance.now() - started;
    expect(tracks[0].notes).toHaveLength(count);
    expect(previewEndTick(tracks)).toBe((count - 1) * 30 + 480);
    expect(elapsed).toBeLessThan(1000);
  });
});

describe("transport timing", () => {
  it("uses document tempo and PPQ for tick/second conversion", () => {
    expect(tickToSeconds(1920, 480, 120)).toBe(2);
    expect(secondsToTick(2, 480, 120)).toBe(1920);
    expect(tickToSeconds(1440, 480, 90)).toBe(2);
  });

  it("validates loop boundaries", () => {
    expect(isValidLoop(0, 1920, 7680)).toBe(true);
    expect(isValidLoop(-1, 1920, 7680)).toBe(false);
    expect(isValidLoop(1920, 1920, 7680)).toBe(false);
    expect(isValidLoop(3840, 1920, 7680)).toBe(false);
    expect(isValidLoop(0, 9000, 7680)).toBe(false);
  });
});
