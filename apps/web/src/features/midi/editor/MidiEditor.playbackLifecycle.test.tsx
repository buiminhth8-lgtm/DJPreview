import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MidiEditor } from "./MidiEditor";
import type { MidiEditorDocument } from "./midiEditorTypes";
import { saveMidiEditorTrack } from "./midiEditorApi";

const editorDocument: MidiEditorDocument = {
  songId: "song-1",
  versionId: "v4",
  ppq: 480,
  bpm: 120,
  timeSignature: [4, 4],
  totalBars: 8,
  tracks: [{
    id: "bass",
    role: "bass",
    name: "bass",
    channel: 2,
    instrument: null,
    isDrum: false,
    notes: [{ id: "b1", pitch: 40, startTick: 0, durationTick: 480, velocity: 100, channel: 2 }],
  }],
};

const reload = vi.fn(async () => undefined);
const stopPreview = vi.fn();

vi.mock("./useMidiEditorDocument", () => ({
  useMidiEditorDocument: () => ({
    document: editorDocument,
    isLoading: false,
    error: null,
    notFound: false,
    reload,
  }),
}));

vi.mock("./useMidiPlayback", () => ({
  useMidiPlayback: () => ({
    scope: "current_track",
    setScope: vi.fn(),
    currentTick: 0,
    isPlaying: true,
    isPreparing: false,
    error: null,
    warnings: [],
    loopEnabled: false,
    loopStartTick: 0,
    loopEndTick: 1920,
    loopValid: true,
    maxTick: 15360,
    play: vi.fn(),
    stop: stopPreview,
    seek: vi.fn(),
    setLoopEnabled: vi.fn(() => true),
    setLoopStartTick: vi.fn(),
    setLoopEndTick: vi.fn(),
  }),
}));

vi.mock("./midiEditorApi", async () => {
  const actual = await vi.importActual<typeof import("./midiEditorApi")>("./midiEditorApi");
  return { ...actual, saveMidiEditorTrack: vi.fn() };
});

beforeEach(() => {
  reload.mockClear();
  stopPreview.mockClear();
  vi.mocked(saveMidiEditorTrack).mockReset();
  vi.mocked(saveMidiEditorTrack).mockResolvedValue({ songId: "song-1", versionId: "v5", warnings: [] });
});

describe("MidiEditor playback lifecycle integration", () => {
  it("stops Preview before Save API", async () => {
    render(<MidiEditor songId="song-1" />);
    fireEvent.doubleClick(globalThis.document.querySelector(".midi-editor__grid")!, { clientX: 100, clientY: 40 });
    fireEvent.click(screen.getByRole("button", { name: "保存 MIDI 修改" }));
    await waitFor(() => expect(saveMidiEditorTrack).toHaveBeenCalled());
    expect(stopPreview).toHaveBeenCalled();
    expect(stopPreview.mock.invocationCallOrder[0]).toBeLessThan(
      vi.mocked(saveMidiEditorTrack).mock.invocationCallOrder[0],
    );
  });

  it("stops Preview before refreshKey document reload (restore/regenerate)", async () => {
    const view = render(<MidiEditor songId="song-1" refreshKey={0} />);
    view.rerender(<MidiEditor songId="song-1" refreshKey={1} />);
    await waitFor(() => expect(reload).toHaveBeenCalled());
    expect(stopPreview).toHaveBeenCalled();
    expect(stopPreview.mock.invocationCallOrder[0]).toBeLessThan(reload.mock.invocationCallOrder[0]);
  });
});
