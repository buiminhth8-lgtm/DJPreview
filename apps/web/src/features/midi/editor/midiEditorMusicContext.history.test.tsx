import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { bassOverlapWarning } from "./midiEditorMusicContext";
import type { MidiEditorDocument } from "./midiEditorTypes";
import { useMidiEditorDraft } from "./useMidiEditorDraft";

const document: MidiEditorDocument = {
  songId: "song-bass",
  versionId: "v1",
  ppq: 480,
  bpm: 100,
  timeSignature: [4, 4],
  totalBars: 4,
  tracks: [{
    id: "bass",
    role: "bass",
    name: "bass",
    channel: 2,
    instrument: "electric_bass_finger",
    isDrum: false,
    notes: [{ id: "b1", pitch: 40, startTick: 0, durationTick: 480, velocity: 90, channel: 2 }],
  }],
};

describe("Bass warning and history", () => {
  it("recomputes from the draft and disappears after Undo", async () => {
    const { result } = renderHook(() => useMidiEditorDraft(document));
    await waitFor(() => expect(result.current.draftNotesByTrack.bass).toHaveLength(1));
    act(() => {
      result.current.insertNotes("bass", [
        { pitch: 43, startTick: 240, durationTick: 480, velocity: 90, channel: 2 },
      ]);
    });
    expect(bassOverlapWarning("bass", result.current.draftNotesByTrack.bass)).not.toBeNull();
    act(() => result.current.undo("bass"));
    expect(bassOverlapWarning("bass", result.current.draftNotesByTrack.bass)).toBeNull();
  });
});
