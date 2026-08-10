// features/midi/editor/MidiEditor.test.tsx（T34.3/34.4）
// 覆盖：document render、默认轨道选择、轨道切换、note.id key、无 MIDI、loading/error。

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";

import { MidiEditor } from "./MidiEditor";
import type { MidiEditorDocument } from "./midiEditorTypes";
import type { MusicSpec } from "../../../api/types";

const docBass: MidiEditorDocument = {
  songId: "song-1",
  versionId: "v4",
  ppq: 480,
  bpm: 120,
  timeSignature: [4, 4],
  totalBars: 8,
  tracks: [
    {
      id: "melody",
      role: "melody",
      name: "melody",
      channel: 0,
      instrument: null,
      isDrum: false,
      notes: [
        { id: "m1", pitch: 72, startTick: 0, durationTick: 480, velocity: 100, channel: 0 },
        { id: "m2", pitch: 74, startTick: 480, durationTick: 240, velocity: 90, channel: 0 },
      ],
    },
    {
      id: "bass",
      role: "bass",
      name: "bass",
      channel: 2,
      instrument: "electric_bass_finger",
      isDrum: false,
      notes: [
        { id: "b1", pitch: 40, startTick: 0, durationTick: 480, velocity: 110, channel: 2 },
        { id: "b2", pitch: 43, startTick: 480, durationTick: 360, velocity: 95, channel: 2 },
      ],
    },
    {
      id: "drums",
      role: "drums",
      name: "drums",
      channel: 9,
      instrument: "standard_drum_kit",
      isDrum: true,
      notes: [{ id: "d1", pitch: 36, startTick: 0, durationTick: 240, velocity: 120, channel: 9 }],
    },
  ],
};

function musicSpec(key = "C"): MusicSpec {
  return {
    version: "0.1",
    title: `${key} project`,
    seed: 1,
    language: "zh-CN",
    prompt: "test",
    tempo: { bpm: 120, feel: null },
    meter: { numerator: 4, denominator: 4 },
    tonality: { key, mode: "major", scale: null },
    length: { bars: 8 },
    style: [],
    mood: [],
    form: [
      { id: "intro", name: "Intro", start_bar: 1, bars: 2, energy: 0.3 },
      { id: "verse", name: "Verse", start_bar: 3, bars: 6, energy: 0.7 },
    ],
    harmony: [
      { section: "intro", progression: [key] },
      { section: "verse", progression: [key, "G"] },
    ],
    tracks: [
      { id: "melody", role: "melody", instrument: "piano", pattern: null, register: null, velocity: 90, enabled_sections: null },
      { id: "bass", role: "bass", instrument: "electric_bass_finger", pattern: null, register: "low", velocity: 90, enabled_sections: null },
      { id: "drums", role: "drums", instrument: "standard_drum_kit", pattern: null, register: null, velocity: 100, enabled_sections: null },
    ],
    notes: null,
  };
}

let mockDocument: MidiEditorDocument | null = docBass;
let mockIsLoading = false;
let mockError: string | null = null;
let mockNotFound = false;

vi.mock("./useMidiEditorDocument", () => ({
  useMidiEditorDocument: () => ({
    document: mockDocument,
    isLoading: mockIsLoading,
    error: mockError,
    notFound: mockNotFound,
    reload: vi.fn(),
  }),
}));

function trackList() {
  return within(screen.getByRole("listbox", { name: "选择轨道" }));
}

describe("MidiEditor", () => {
  it("renders track selector with real track data", () => {
    render(<MidiEditor songId="song-1" />);
    const list = trackList();
    expect(list.getByRole("option", { name: /melody/ })).toBeInTheDocument();
    expect(list.getByRole("option", { name: /bass/ })).toBeInTheDocument();
    expect(list.getByRole("option", { name: /drums/ })).toBeInTheDocument();
  });

  it("default selects first track with notes (melody) and renders its notes", () => {
    render(<MidiEditor songId="song-1" />);
    const selected = trackList().getByRole("option", { selected: true });
    expect(selected).toHaveTextContent(/melody/);
    expect(screen.getByText(/Track: melody/)).toBeInTheDocument();
  });

  it("switching to bass shows only bass notes", () => {
    render(<MidiEditor songId="song-1" />);
    fireEvent.click(trackList().getByRole("option", { name: /bass/ }));
    expect(trackList().getByRole("option", { selected: true })).toHaveTextContent(/bass/);
    expect(screen.getByText(/Track: bass/)).toBeInTheDocument();
  });

  it("switching to drums shows drum notes", () => {
    render(<MidiEditor songId="song-1" />);
    fireEvent.click(trackList().getByRole("option", { name: /drums/ }));
    expect(trackList().getByRole("option", { selected: true })).toHaveTextContent(/drums/);
    expect(screen.getByText(/Track: drums/)).toBeInTheDocument();
    for (const label of ["Kick", "Snare", "Closed Hat", "Open Hat", "Crash", "Ride"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("notes render with canonical note.id as data attribute", () => {
    render(<MidiEditor songId="song-1" />);
    const roll = document.querySelector('[data-note-count="2"]');
    expect(roll).not.toBeNull();
    expect(roll!.querySelector('[data-note-id="m1"]')).not.toBeNull();
    fireEvent.click(trackList().getByRole("option", { name: /bass/ }));
    const bassRoll = document.querySelector('[data-note-count="2"]');
    expect(bassRoll!.querySelector('[data-note-id="b1"]')).not.toBeNull();
    expect(bassRoll!.querySelector('[data-note-id="m1"]')).toBeNull();
  });

  it("renders no-MIDI empty state when document is null with notFound", () => {
    mockDocument = null;
    mockNotFound = true;
    render(<MidiEditor songId="song-1" />);
    expect(screen.getByText("尚未生成 MIDI")).toBeInTheDocument();
    mockDocument = docBass;
    mockNotFound = false;
  });

  it("renders loading state", () => {
    mockDocument = null;
    mockIsLoading = true;
    render(<MidiEditor songId="song-1" />);
    expect(screen.getByText(/正在加载 MIDI/)).toBeInTheDocument();
    mockDocument = docBass;
    mockIsLoading = false;
  });

  it("renders error state", () => {
    mockDocument = null;
    mockError = "boom";
    render(<MidiEditor songId="song-1" />);
    expect(screen.getByText("MIDI 加载失败")).toBeInTheDocument();
    expect(screen.getByText("boom")).toBeInTheDocument();
    mockDocument = docBass;
    mockError = null;
  });

  it("clears selection when the loaded project/version document changes", () => {
    const { rerender } = render(<MidiEditor songId="song-1" />);
    fireEvent.pointerDown(document.querySelector('[data-note-id="m1"]')!);
    expect(screen.getByTestId("selected-note-count")).toHaveTextContent("Selected: 1");
    mockDocument = { ...docBass, songId: "song-2", versionId: "v5" };
    rerender(<MidiEditor songId="song-2" />);
    expect(screen.getByTestId("selected-note-count")).toHaveTextContent("Selected: 0");
    mockDocument = docBass;
  });

  it("renders session-only semantic toggles without crossing the manual MIDI edit boundary", () => {
    const source = musicSpec();
    const before = JSON.stringify(source);
    render(<MidiEditor songId="song-1" musicSpec={source} />);
    expect(screen.getByRole("button", { name: "Scale ✓" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Chords ✓" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Sections ✓" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("section-overlay")).toBeInTheDocument();
    expect(screen.getByTestId("chord-overlay")).toBeInTheDocument();
    expect(document.querySelector('.midi-editor__pitch-row[data-midi-pitch="72"]')).toHaveAttribute("data-scale-kind", "root");
    fireEvent.click(screen.getByRole("button", { name: "Scale ✓" }));
    expect(screen.getByRole("button", { name: "Scale" })).toHaveAttribute("aria-pressed", "false");
    expect(document.querySelector('.midi-editor__pitch-row[data-midi-pitch="72"]')).not.toHaveAttribute("data-scale-kind");
    expect(screen.getByRole("button", { name: "保存 MIDI 修改" })).toBeDisabled();
    expect(JSON.stringify(source)).toBe(before);
  });

  it("replaces project/version music context without leaking the previous key", () => {
    const { rerender } = render(<MidiEditor songId="song-1" musicSpec={musicSpec("C")} />);
    expect(document.querySelector('.midi-editor__pitch-row[data-midi-pitch="72"]')).toHaveAttribute("data-scale-kind", "root");
    mockDocument = { ...docBass, songId: "song-2", versionId: "v5" };
    rerender(<MidiEditor songId="song-2" musicSpec={musicSpec("D")} />);
    expect(screen.getByText("Scale: D major")).toBeInTheDocument();
    expect(document.querySelector('.midi-editor__pitch-row[data-midi-pitch="72"]')).toHaveAttribute("data-scale-kind", "out-of-scale");
    mockDocument = docBass;
  });

  it("rebuilds semantic context after restore/regenerate refresh", async () => {
    const { rerender } = render(<MidiEditor songId="song-1" refreshKey={0} musicSpec={musicSpec("C")} />);
    expect(screen.getByText("Scale: C major")).toBeInTheDocument();
    mockDocument = { ...docBass, versionId: "v6" };
    rerender(<MidiEditor songId="song-1" refreshKey={1} musicSpec={musicSpec("D")} />);
    expect(await screen.findByText("Scale: D major")).toBeInTheDocument();
    expect(screen.queryByText("Scale: C major")).toBeNull();
    mockDocument = docBass;
  });

  it("shows overlap guidance only on the canonical Bass role", () => {
    mockDocument = {
      ...docBass,
      tracks: docBass.tracks.map((track) => track.id === "bass"
        ? { ...track, notes: [
            { id: "b1", pitch: 40, startTick: 0, durationTick: 600, velocity: 110, channel: 2 },
            { id: "b2", pitch: 43, startTick: 480, durationTick: 360, velocity: 95, channel: 2 },
          ] }
        : track),
    };
    render(<MidiEditor songId="song-1" musicSpec={musicSpec()} />);
    expect(screen.queryByText(/低频浑浊/)).toBeNull();
    fireEvent.click(trackList().getByRole("option", { name: /bass/ }));
    expect(screen.getByText(/低频浑浊/)).toBeInTheDocument();
    fireEvent.click(trackList().getByRole("option", { name: /melody/ }));
    expect(screen.queryByText(/低频浑浊/)).toBeNull();
    mockDocument = docBass;
  });

  it("hides unavailable music context features", () => {
    render(<MidiEditor songId="song-1" />);
    expect(screen.queryByLabelText("Music context overlays")).toBeNull();
  });
});
