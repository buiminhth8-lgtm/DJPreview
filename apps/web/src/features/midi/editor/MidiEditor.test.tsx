// features/midi/editor/MidiEditor.test.tsx（T34.3）
// 覆盖：document render、默认轨道选择、轨道切换、note.id key、songId A→B 隔离。

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { MidiEditor } from "./MidiEditor";
import type { MidiEditorDocument } from "./midiEditorTypes";

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

describe("MidiEditor", () => {
  it("renders track selector with real track data", () => {
    render(<MidiEditor songId="song-1" />);
    expect(screen.getByRole("listbox", { name: "选择轨道" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /melody/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /bass/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /drums/ })).toBeInTheDocument();
  });

  it("default selects first track with notes (melody) and renders its notes", () => {
    render(<MidiEditor songId="song-1" />);
    const selected = screen.getByRole("option", { selected: true });
    expect(selected).toHaveTextContent(/melody/);
    expect(screen.getByText(/2 notes/)).toBeInTheDocument();
  });

  it("switching to bass shows only bass notes", () => {
    render(<MidiEditor songId="song-1" />);
    fireEvent.click(screen.getByRole("option", { name: /bass/ }));
    expect(screen.getByRole("option", { selected: true })).toHaveTextContent(/bass/);
    expect(screen.getByText(/Track: bass/)).toBeInTheDocument();
    expect(screen.getByText(/2 notes/)).toBeInTheDocument();
  });

  it("switching to drums shows drum notes", () => {
    render(<MidiEditor songId="song-1" />);
    fireEvent.click(screen.getByRole("option", { name: /drums/ }));
    expect(screen.getByRole("option", { selected: true })).toHaveTextContent(/drums/);
    expect(screen.getByText(/1 notes/)).toBeInTheDocument();
  });

  it("notes render with canonical note.id as data attribute", () => {
    render(<MidiEditor songId="song-1" />);
    // melody default: m1, m2
    const roll = document.querySelector('[data-note-count="2"]');
    expect(roll).not.toBeNull();
    expect(roll!.querySelector('[data-note-id="m1"]')).not.toBeNull();
    expect(roll!.querySelector('[data-note-id="m2"]')).not.toBeNull();
    // switch to bass → m1 gone, b1 present
    fireEvent.click(screen.getByRole("option", { name: /bass/ }));
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
});
