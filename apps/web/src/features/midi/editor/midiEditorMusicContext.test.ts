import { describe, expect, it } from "vitest";

import type { MusicSpec } from "../../../api/types";
import {
  GM_DRUM_LABELS,
  bassOverlapWarning,
  buildMidiEditorMusicContext,
  buildScaleContext,
  classifyScalePitch,
  computeDrumPitchRange,
  countNoteOverlapStarts,
} from "./midiEditorMusicContext";
import type { MidiEditorNote } from "./midiEditorTypes";

function spec(overrides: Partial<MusicSpec> = {}): MusicSpec {
  return {
    version: "0.1",
    title: "Context fixture",
    seed: 1,
    language: "zh-CN",
    prompt: "test",
    tempo: { bpm: 120, feel: null },
    meter: { numerator: 4, denominator: 4 },
    tonality: { key: "C", mode: "major", scale: null },
    length: { bars: 8 },
    style: [],
    mood: [],
    form: [{ id: "verse", name: "Verse", start_bar: 1, bars: 8, energy: 0.6 }],
    harmony: [{ section: "verse", progression: ["C", "G", "Am", "F"] }],
    tracks: [{ id: "bass", role: "bass", instrument: "electric_bass_finger", pattern: null, register: "low", velocity: 90, enabled_sections: null }],
    notes: null,
    ...overrides,
  };
}

function note(id: string, startTick: number, durationTick: number): MidiEditorNote {
  return { id, pitch: 40, startTick, durationTick, velocity: 90, channel: 2 };
}

describe("MidiEditorMusicContext", () => {
  it("classifies C major and A minor roots, scale tones and chromatic tones", () => {
    const cMajor = buildScaleContext(spec())!;
    expect(classifyScalePitch(60, cMajor)).toBe("root");
    expect(classifyScalePitch(62, cMajor)).toBe("in-scale");
    expect(classifyScalePitch(61, cMajor)).toBe("out-of-scale");

    const aMinor = buildScaleContext(spec({ tonality: { key: "A", mode: "minor", scale: null } }))!;
    expect(classifyScalePitch(57, aMinor)).toBe("root");
    expect(classifyScalePitch(60, aMinor)).toBe("in-scale");
    expect(classifyScalePitch(61, aMinor)).toBe("out-of-scale");
  });

  it("supports existing scale vocabulary and hides unsupported/missing scale data", () => {
    expect(buildScaleContext(spec({ tonality: { key: "Bb", mode: "major", scale: null } }))?.rootPitchClass).toBe(10);
    expect(buildScaleContext(spec({ tonality: { key: "D", mode: "dorian", scale: null } }))).not.toBeNull();
    expect(buildScaleContext(spec({ tonality: { key: "C", mode: "major", scale: "c-major" } }))?.mode).toBe("major");
    expect(buildScaleContext(spec({ tonality: { key: "D", mode: "minor", scale: "d-natural-minor" } }))?.mode).toBe("natural_minor");
    expect(buildScaleContext(spec({ tonality: { key: "C", mode: "pentatonic", scale: "c-major-pentatonic" } }))?.mode).toBe("major_pentatonic");
    expect(buildScaleContext(spec({ tonality: { key: "H", mode: "major", scale: null } }))).toBeNull();
    expect(buildScaleContext(spec({ tonality: { key: "C", mode: "whole_tone", scale: "c-whole-tone" } }))).toBeNull();
  });

  it("maps sections and one-chord-per-bar progression to canonical 6/8 ticks", () => {
    const source = spec({
      meter: { numerator: 6, denominator: 8 },
      length: { bars: 5 },
      form: [{ id: "verse", name: "Verse", start_bar: 3, bars: 3, energy: 0.5 }],
      harmony: [{ section: "verse", progression: ["Dm", "G"] }],
    });
    const before = JSON.stringify(source);
    const context = buildMidiEditorMusicContext(source, 480, source.meter, 5);
    expect(context.totalTicks).toBe(7200); // 5 * (6 eighth-note beats * 240 ticks)
    expect(context.sections[0]).toMatchObject({ startTick: 2880, endTick: 7200, startBar: 3 });
    expect(context.chords.map((chord) => [chord.symbol, chord.startTick, chord.endTick])).toEqual([
      ["Dm", 2880, 4320],
      ["G", 4320, 5760],
      ["Dm", 5760, 7200],
    ]);
    expect(JSON.stringify(source)).toBe(before);
  });

  it("keeps progression summary but emits no timed chord when section timing is unavailable", () => {
    const context = buildMidiEditorMusicContext(
      spec({ form: [], harmony: [{ section: "unknown", progression: ["C", "F"] }] }),
      480,
      { numerator: 4, denominator: 4 },
    );
    expect(context.sections).toEqual([]);
    expect(context.chords).toEqual([]);
    expect(context.chordSummary).toEqual(["unknown: C – F"]);
  });

  it("derives canonical track roles and common GM drum semantics", () => {
    const context = buildMidiEditorMusicContext(spec(), 480, { numerator: 4, denominator: 4 });
    expect(context.trackRoles.get("bass")).toBe("bass");
    expect(GM_DRUM_LABELS.get(36)).toBe("Kick");
    expect(GM_DRUM_LABELS.get(38)).toBe("Snare");
    expect(GM_DRUM_LABELS.get(42)).toBe("Closed Hat");
    expect(GM_DRUM_LABELS.get(46)).toBe("Open Hat");
    expect(GM_DRUM_LABELS.get(49)).toBe("Crash");
    expect(GM_DRUM_LABELS.get(51)).toBe("Ride");
    expect(computeDrumPitchRange([{ pitch: 35 }, { pitch: 60 }])).toEqual({ minPitch: 35, maxPitch: 60 });
  });

  it("warns only for Bass overlap and treats touching note boundaries as monophonic", () => {
    const notes = [note("n3", 960, 240), note("n1", 0, 480), note("n2", 240, 240)];
    expect(countNoteOverlapStarts(notes)).toBe(1);
    expect(bassOverlapWarning("bass", notes)).toMatch(/1 处同时发声/);
    expect(bassOverlapWarning("melody", notes)).toBeNull();
    expect(countNoteOverlapStarts([note("a", 0, 480), note("b", 480, 480)])).toBe(0);
  });

  it("handles 500/1000/3000-note overlap scans without quadratic pair expansion", () => {
    const started = performance.now();
    for (const size of [500, 1000, 3000]) {
      const notes = Array.from({ length: size }, (_, index) => note(`n-${size}-${index}`, index, 2));
      expect(countNoteOverlapStarts(notes)).toBe(size - 1);
    }
    expect(performance.now() - started).toBeLessThan(1000);
  });
});
