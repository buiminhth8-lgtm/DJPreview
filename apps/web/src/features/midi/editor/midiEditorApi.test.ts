// features/midi/editor/midiEditorApi.test.ts（T34.1）
// 验证后端 snake_case → 前端 camelCase 归一化与 hook 的竞态处理。

import { describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";

import { mapMidiEditorDocument } from "./midiEditorApi";
import { useMidiEditorDocument } from "./useMidiEditorDocument";
import * as midiEditorApi from "./midiEditorApi";

const rawDoc = {
  song_id: "song-1",
  version_id: "v4",
  ppq: 480,
  bpm: 120,
  time_signature: [4, 4] as [number, number],
  total_bars: 8,
  tracks: [
    {
      id: "bass",
      role: "bass",
      name: "bass",
      channel: 2,
      instrument: "electric_bass_finger",
      is_drum: false,
      notes: [
        { id: "n1", pitch: 40, start_tick: 0, duration_tick: 480, velocity: 110, channel: 2 },
      ],
    },
    {
      id: "drums",
      role: "drums",
      name: "drums",
      channel: 9,
      instrument: "standard_drum_kit",
      is_drum: true,
      notes: [{ id: "d1", pitch: 36, start_tick: 0, duration_tick: 240, velocity: 120, channel: 9 }],
    },
  ],
};

describe("mapMidiEditorDocument", () => {
  it("normalizes snake_case to camelCase and keeps ticks", () => {
    const doc = mapMidiEditorDocument(rawDoc);
    expect(doc.songId).toBe("song-1");
    expect(doc.versionId).toBe("v4");
    expect(doc.ppq).toBe(480);
    expect(doc.timeSignature).toEqual([4, 4]);
    const bass = doc.tracks.find((t) => t.id === "bass");
    expect(bass?.notes[0]).toMatchObject({ startTick: 0, durationTick: 480 });
    const drums = doc.tracks.find((t) => t.id === "drums");
    expect(drums?.isDrum).toBe(true);
    expect(drums?.notes[0].channel).toBe(9);
  });
});

describe("useMidiEditorDocument", () => {
  it("loads document on mount", async () => {
    vi.spyOn(midiEditorApi, "getMidiEditorDocument").mockResolvedValue(
      mapMidiEditorDocument(rawDoc),
    );
    const { result } = renderHook(() => useMidiEditorDocument("song-1"));
    expect(result.current.isLoading).toBe(true);
    await waitFor(() => expect(result.current.document?.songId).toBe("song-1"));
    expect(result.current.error).toBeNull();
  });

  it("does not request when songId missing", async () => {
    const spy = vi.spyOn(midiEditorApi, "getMidiEditorDocument");
    renderHook(() => useMidiEditorDocument(null));
    expect(spy).not.toHaveBeenCalled();
  });

  it("surfaces error state", async () => {
    vi.spyOn(midiEditorApi, "getMidiEditorDocument").mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useMidiEditorDocument("song-1"));
    await waitFor(() => expect(result.current.error).toBe("boom"));
    expect(result.current.document).toBeNull();
  });

  it("clears stale result when songId changes", async () => {
    const spy = vi.spyOn(midiEditorApi, "getMidiEditorDocument");
    const gates = new Map<string, (v: unknown) => void>();
    spy.mockImplementation((songId: string) => {
      if (songId === "song-a") {
        return new Promise((resolve) => gates.set("song-a", resolve)).then(() =>
          mapMidiEditorDocument({ ...rawDoc, song_id: "song-a" }),
        );
      }
      return Promise.resolve(mapMidiEditorDocument({ ...rawDoc, song_id: "song-b" }));
    });
    const { result, rerender } = renderHook(({ id }) => useMidiEditorDocument(id), {
      initialProps: { id: "song-a" },
    });
    rerender({ id: "song-b" });
    await waitFor(() => expect(result.current.document?.songId).toBe("song-b"));
    // 旧的 song-a 请求晚返回，不应覆盖 song-b
    await act(async () => {
      gates.get("song-a")?.(mapMidiEditorDocument({ ...rawDoc, song_id: "song-a" }));
    });
    expect(result.current.document?.songId).toBe("song-b");
  });
});
