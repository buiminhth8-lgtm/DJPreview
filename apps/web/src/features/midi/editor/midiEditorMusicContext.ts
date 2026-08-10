// T34.9: read-only musical semantics derived from the canonical MusicSpec.
// This module never mutates MIDI notes or MusicSpec and never invents a second project schema.

import type { MusicSpec } from "../../../api/types";
import type { MeterInfo } from "./midiEditorLayout";
import { ticksPerBar } from "./midiEditorLayout";
import type { MidiEditorNote } from "./midiEditorTypes";

export type ScalePitchKind = "root" | "in-scale" | "out-of-scale";

export interface MidiEditorScaleContext {
  tonic: string;
  mode: string;
  label: string;
  rootPitchClass: number;
  pitchClasses: ReadonlySet<number>;
}

export interface MidiEditorSectionMarker {
  id: string;
  name: string;
  startBar: number;
  bars: number;
  startTick: number;
  endTick: number;
  energy: number;
}

export interface MidiEditorChordMarker {
  sectionId: string;
  symbol: string;
  bar: number;
  startTick: number;
  endTick: number;
}

export interface MidiEditorMusicContext {
  scale: MidiEditorScaleContext | null;
  sections: MidiEditorSectionMarker[];
  chords: MidiEditorChordMarker[];
  chordSummary: string[];
  trackRoles: ReadonlyMap<string, string>;
  totalTicks: number;
}

const NOTE_PITCH_CLASSES: Record<string, number> = {
  C: 0, "B#": 0, "C#": 1, DB: 1, D: 2, "D#": 3, EB: 3,
  E: 4, FB: 4, "E#": 5, F: 5, "F#": 6, GB: 6, G: 7,
  "G#": 8, AB: 8, A: 9, "A#": 10, BB: 10, B: 11, CB: 11,
};

// Names mirror the vocabulary already accepted by MusicSpec/theory.scales.
const SCALE_INTERVALS: Record<string, readonly number[]> = {
  major: [0, 2, 4, 5, 7, 9, 11],
  ionian: [0, 2, 4, 5, 7, 9, 11],
  minor: [0, 2, 3, 5, 7, 8, 10],
  natural_minor: [0, 2, 3, 5, 7, 8, 10],
  aeolian: [0, 2, 3, 5, 7, 8, 10],
  harmonic_minor: [0, 2, 3, 5, 7, 8, 11],
  melodic_minor: [0, 2, 3, 5, 7, 9, 11],
  dorian: [0, 2, 3, 5, 7, 9, 10],
  pentatonic: [0, 2, 4, 7, 9],
  major_pentatonic: [0, 2, 4, 7, 9],
  minor_pentatonic: [0, 3, 5, 7, 10],
};

// Labels mirror packages/music_core/midi/midi_constants.py (canonical GM pitches).
export const GM_DRUM_LABELS: ReadonlyMap<number, string> = new Map([
  [36, "Kick"], [37, "Side Stick"], [38, "Snare"], [39, "Clap"],
  [42, "Closed Hat"], [44, "Pedal Hat"], [45, "Low Tom"],
  [46, "Open Hat"], [47, "Mid Tom"], [49, "Crash"],
  [50, "High Tom"], [51, "Ride"],
]);

function normalizeScaleName(value: string | null | undefined): string {
  return (value ?? "").trim().toLowerCase().replace(/[\s-]+/g, "_");
}

export function tonicToPitchClass(tonic: string | null | undefined): number | null {
  const normalized = (tonic ?? "").trim().replace(/♯/g, "#").replace(/♭/g, "b").toUpperCase();
  return NOTE_PITCH_CLASSES[normalized] ?? null;
}

export function buildScaleContext(musicSpec: MusicSpec): MidiEditorScaleContext | null {
  const rootPitchClass = tonicToPitchClass(musicSpec.tonality?.key);
  if (rootPitchClass == null) return null;
  const scaleName = normalizeScaleName(musicSpec.tonality?.scale);
  const modeName = normalizeScaleName(musicSpec.tonality?.mode);
  const namedSuffix = Object.keys(SCALE_INTERVALS)
    .sort((a, b) => b.length - a.length)
    .find((name) => scaleName.endsWith(`_${name}`));
  const requested = [scaleName, namedSuffix, modeName]
    .find((name): name is string => Boolean(name && SCALE_INTERVALS[name])) ?? "";
  const intervals = SCALE_INTERVALS[requested];
  if (!intervals) return null;
  return {
    tonic: musicSpec.tonality.key,
    mode: requested,
    label: `${musicSpec.tonality.key} ${requested.replace(/_/g, " ")}`,
    rootPitchClass,
    pitchClasses: new Set(intervals.map((interval) => (rootPitchClass + interval) % 12)),
  };
}

export function classifyScalePitch(pitch: number, scale: MidiEditorScaleContext): ScalePitchKind {
  const pitchClass = ((Math.round(pitch) % 12) + 12) % 12;
  if (pitchClass === scale.rootPitchClass) return "root";
  return scale.pitchClasses.has(pitchClass) ? "in-scale" : "out-of-scale";
}

export function buildMidiEditorMusicContext(
  musicSpec: MusicSpec,
  ppq: number,
  meter: MeterInfo,
  documentTotalBars = 0,
): MidiEditorMusicContext {
  const perBar = ticksPerBar(ppq, meter);
  const specBars = Number.isFinite(musicSpec.length?.bars) ? Math.max(0, musicSpec.length.bars) : 0;
  const totalBars = Math.max(specBars, Math.max(0, documentTotalBars));
  const totalTicks = totalBars * perBar;

  const sections: MidiEditorSectionMarker[] = (musicSpec.form ?? [])
    .filter((section) => section.start_bar >= 1 && section.bars >= 1)
    .map((section) => ({
      id: section.id,
      name: section.name,
      startBar: section.start_bar,
      bars: section.bars,
      startTick: (section.start_bar - 1) * perBar,
      endTick: (section.start_bar - 1 + section.bars) * perBar,
      energy: section.energy,
    }))
    .sort((a, b) => a.startTick - b.startTick || a.id.localeCompare(b.id));

  const sectionById = new Map(sections.map((section) => [section.id, section]));
  const chords: MidiEditorChordMarker[] = [];
  const chordSummary: string[] = [];
  for (const harmony of musicSpec.harmony ?? []) {
    const progression = (harmony.progression ?? []).filter((symbol) => Boolean(symbol?.trim()));
    if (!progression.length) continue;
    chordSummary.push(`${harmony.section}: ${progression.join(" – ")}`);
    const section = sectionById.get(harmony.section);
    if (!section) continue;
    // Canonical composer rule (harmony_engine.build_bar_harmony): one chord per bar,
    // cycling the MusicSpec progression for the full section duration.
    for (let index = 0; index < section.bars; index += 1) {
      const startTick = section.startTick + index * perBar;
      chords.push({
        sectionId: section.id,
        symbol: progression[index % progression.length],
        bar: section.startBar + index,
        startTick,
        endTick: startTick + perBar,
      });
    }
  }

  return {
    scale: buildScaleContext(musicSpec),
    sections,
    chords: chords.sort((a, b) => a.startTick - b.startTick || a.sectionId.localeCompare(b.sectionId)),
    chordSummary,
    trackRoles: new Map(
      (musicSpec.tracks ?? []).map((track) => [track.id, (track.role ?? "").trim().toLowerCase()]),
    ),
    totalTicks,
  };
}

export function computeDrumPitchRange(
  notes: Array<{ pitch: number }>,
): { minPitch: number; maxPitch: number } {
  let minPitch = Math.min(...GM_DRUM_LABELS.keys());
  let maxPitch = Math.max(...GM_DRUM_LABELS.keys());
  for (const note of notes) {
    const pitch = Math.max(0, Math.min(127, Math.round(note.pitch)));
    minPitch = Math.min(minPitch, pitch);
    maxPitch = Math.max(maxPitch, pitch);
  }
  return { minPitch, maxPitch };
}

/** Count notes whose start occurs while at least one earlier note is still sounding. O(n log n). */
export function countNoteOverlapStarts(notes: readonly MidiEditorNote[]): number {
  if (notes.length < 2) return 0;
  const ordered = [...notes].sort(
    (a, b) => a.startTick - b.startTick || a.startTick + a.durationTick - (b.startTick + b.durationTick),
  );
  let furthestEnd = ordered[0].startTick + ordered[0].durationTick;
  let overlaps = 0;
  for (let index = 1; index < ordered.length; index += 1) {
    const note = ordered[index];
    if (note.startTick < furthestEnd) overlaps += 1;
    furthestEnd = Math.max(furthestEnd, note.startTick + note.durationTick);
  }
  return overlaps;
}

export function bassOverlapWarning(
  role: string | null | undefined,
  notes: readonly MidiEditorNote[],
): string | null {
  if ((role ?? "").trim().toLowerCase() !== "bass") return null;
  const overlaps = countNoteOverlapStarts(notes);
  if (!overlaps) return null;
  return `Bass 轨检测到 ${overlaps} 处同时发声；这可能造成低频浑浊。仅提示，不会自动修改音符。`;
}
