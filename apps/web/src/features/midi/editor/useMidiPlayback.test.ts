import { act, renderHook } from "@testing-library/react";
import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { MidiEditorDocument } from "./midiEditorTypes";
import { useMidiPlayback } from "./useMidiPlayback";
import { createMidiEditorPreview, deleteMidiEditorPreview } from "./midiEditorApi";

vi.mock("./midiEditorApi", async () => {
  const actual = await vi.importActual<typeof import("./midiEditorApi")>("./midiEditorApi");
  return {
    ...actual,
    createMidiEditorPreview: vi.fn(),
    deleteMidiEditorPreview: vi.fn(),
  };
});

const document: MidiEditorDocument = {
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
      notes: [{ id: "m1", pitch: 72, startTick: 0, durationTick: 480, velocity: 100, channel: 0 }],
    },
    {
      id: "bass",
      role: "bass",
      name: "bass",
      channel: 2,
      instrument: null,
      isDrum: false,
      notes: [{ id: "b1", pitch: 40, startTick: 0, durationTick: 480, velocity: 100, channel: 2 }],
    },
  ],
};

class FakeAudio extends EventTarget {
  currentTime = 0;
  preload = "";
  src = "";
  play = vi.fn(async () => undefined);
  pause = vi.fn();
  load = vi.fn();
  removeAttribute = vi.fn((name: string) => {
    if (name === "src") this.src = "";
  });
}

let rafId = 0;
let rafCallbacks = new Map<number, FrameRequestCallback>();

function nextRaf(): void {
  const next = [...rafCallbacks.entries()].sort((a, b) => b[0] - a[0])[0];
  if (!next) throw new Error("没有待执行 RAF");
  rafCallbacks.delete(next[0]);
  next[1](performance.now());
}

beforeEach(() => {
  rafId = 0;
  rafCallbacks = new Map();
  vi.stubGlobal("requestAnimationFrame", vi.fn((callback: FrameRequestCallback) => {
    rafId += 1;
    rafCallbacks.set(rafId, callback);
    return rafId;
  }));
  vi.stubGlobal("cancelAnimationFrame", vi.fn((id: number) => {
    rafCallbacks.delete(id);
  }));
  vi.mocked(createMidiEditorPreview).mockReset();
  vi.mocked(deleteMidiEditorPreview).mockReset();
  vi.mocked(createMidiEditorPreview).mockResolvedValue({
    token: "token-1",
    streamUrl: "/api/v1/preview/stream",
    cleanupUrl: "/api/v1/preview/token-1",
    durationSeconds: 8,
    warnings: [],
  });
  vi.mocked(deleteMidiEditorPreview).mockResolvedValue(true);
});

afterAll(() => vi.unstubAllGlobals());

function renderPlayback(audio: FakeAudio, doc = document) {
  return renderHook(
    ({ currentDocument }) =>
      useMidiPlayback({
        songId: currentDocument.songId,
        document: currentDocument,
        selectedTrackId: "bass",
        draftNotesByTrack: {
          bass: [{ id: "draft", pitch: 45, startTick: 1920, durationTick: 480, velocity: 90, channel: 2 }],
        },
        audioFactory: () => audio as unknown as HTMLAudioElement,
      }),
    { initialProps: { currentDocument: doc } },
  );
}

describe("useMidiPlayback", () => {
  it("plays selected draft from the selected playhead tick and Stop performs allNotesOff", async () => {
    const audio = new FakeAudio();
    const { result } = renderPlayback(audio);
    act(() => result.current.seek(1920));
    await act(async () => result.current.play());

    expect(createMidiEditorPreview).toHaveBeenCalledWith(
      "song-1",
      {
        scope: "current_track",
        tracks: [{
          trackId: "bass",
          notes: [{ id: "draft", pitch: 45, startTick: 1920, durationTick: 480, velocity: 90, channel: 2 }],
        }],
      },
    );
    expect(audio.currentTime).toBe(2);
    expect(result.current.isPlaying).toBe(true);

    act(() => result.current.stop());
    expect(audio.pause).toHaveBeenCalled();
    expect(audio.removeAttribute).toHaveBeenCalledWith("src");
    expect(audio.load).toHaveBeenCalled();
    expect(deleteMidiEditorPreview).toHaveBeenCalledWith("/api/v1/preview/token-1");
    expect(result.current.isPlaying).toBe(false);
  });

  it("All Tracks sends saved melody plus current bass draft", async () => {
    const audio = new FakeAudio();
    const { result } = renderPlayback(audio);
    act(() => result.current.setScope("all_tracks"));
    await act(async () => result.current.play());
    const input = vi.mocked(createMidiEditorPreview).mock.calls[0][1];
    expect(input.scope).toBe("all_tracks");
    expect(input.tracks.map((track) => track.trackId)).toEqual(["melody", "bass"]);
    expect(input.tracks[0].notes[0].id).toBe("m1");
    expect(input.tracks[1].notes[0].id).toBe("draft");
  });

  it("loops at endTick by seeking the same audio resource to startTick", async () => {
    const audio = new FakeAudio();
    const { result } = renderPlayback(audio);
    act(() => result.current.setLoopStartTick(480));
    act(() => result.current.setLoopEndTick(960));
    act(() => expect(result.current.setLoopEnabled(true)).toBe(true));
    await act(async () => result.current.play());
    expect(audio.currentTime).toBe(0.5);

    audio.currentTime = 1.1;
    act(() => nextRaf());
    expect(audio.currentTime).toBe(0.5);
    expect(result.current.currentTick).toBe(480);
    expect(result.current.isPlaying).toBe(true);
  });

  it("playback end and document version switch both clean active audio", async () => {
    const audio = new FakeAudio();
    const { result } = renderPlayback(audio);
    await act(async () => result.current.play());
    act(() => audio.dispatchEvent(new Event("ended")));
    expect(result.current.isPlaying).toBe(false);
    expect(audio.pause).toHaveBeenCalled();

    const nextAudio = new FakeAudio();
    const second = renderPlayback(nextAudio);
    await act(async () => second.result.current.play());
    second.rerender({ currentDocument: { ...document, versionId: "v5" } });
    expect(nextAudio.pause).toHaveBeenCalled();
    expect(second.result.current.isPlaying).toBe(false);
  });

  it("rejects invalid loop regions", () => {
    const audio = new FakeAudio();
    const { result } = renderPlayback(audio);
    act(() => result.current.setLoopStartTick(1920));
    act(() => result.current.setLoopEndTick(1920));
    act(() => expect(result.current.setLoopEnabled(true)).toBe(false));
    expect(result.current.loopEnabled).toBe(false);
    expect(result.current.error).toMatch(/Loop 区域无效/);
  });

  it("Stop during preparation deletes the scratch resource when the stale response arrives", async () => {
    const audio = new FakeAudio();
    let resolvePreview!: (value: Awaited<ReturnType<typeof createMidiEditorPreview>>) => void;
    vi.mocked(createMidiEditorPreview).mockImplementationOnce(
      () => new Promise((resolve) => { resolvePreview = resolve; }),
    );
    const { result } = renderPlayback(audio);
    let pending!: Promise<void>;
    act(() => {
      pending = result.current.play();
    });
    expect(result.current.isPreparing).toBe(true);
    act(() => result.current.stop());
    expect(result.current.isPreparing).toBe(false);

    await act(async () => {
      resolvePreview({
        token: "late-token",
        streamUrl: "/api/v1/preview/late/stream",
        cleanupUrl: "/api/v1/preview/late",
        durationSeconds: 8,
        warnings: [],
      });
      await pending;
    });
    expect(deleteMidiEditorPreview).toHaveBeenCalledWith("/api/v1/preview/late");
    expect(audio.play).not.toHaveBeenCalled();
  });
});
