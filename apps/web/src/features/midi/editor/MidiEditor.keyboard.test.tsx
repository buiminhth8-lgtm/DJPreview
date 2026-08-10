// features/midi/editor/MidiEditor.keyboard.test.tsx（T34.4）
// 回归：Delete/Backspace 在输入框聚焦时不删除 Note；在空白时删除选中 Note。

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { MidiEditor } from "./MidiEditor";
import type { MidiEditorDocument } from "./midiEditorTypes";

const doc: MidiEditorDocument = {
  songId: "s1",
  versionId: "v4",
  ppq: 480,
  bpm: 120,
  timeSignature: [4, 4],
  totalBars: 8,
  tracks: [
    {
      id: "bass",
      role: "bass",
      name: "bass",
      channel: 2,
      instrument: "electric_bass_finger",
      isDrum: false,
      notes: [{ id: "b1", pitch: 40, startTick: 0, durationTick: 480, velocity: 110, channel: 2 }],
    },
    {
      id: "melody",
      role: "melody",
      name: "melody",
      channel: 0,
      instrument: null,
      isDrum: false,
      notes: [{ id: "m1", pitch: 72, startTick: 0, durationTick: 480, velocity: 100, channel: 0 }],
    },
  ],
};

vi.mock("./useMidiEditorDocument", () => ({
  useMidiEditorDocument: () => ({
    document: doc,
    isLoading: false,
    error: null,
    notFound: false,
    reload: vi.fn(),
  }),
}));

describe("MidiEditor keyboard guard", () => {
  it("Delete removes the selected note", () => {
    render(<MidiEditor songId="s1" />);
    // select bass note b1 by clicking its rect
    const note = document.querySelector('[data-note-id="b1"]');
    fireEvent.pointerDown(note!);
    // note 40 = E2; footer text may be split across nodes → check textContent
    const selectedSpan = document.querySelector(".midi-editor__selected-note");
    expect(selectedSpan?.textContent).toContain("E2");
    expect(selectedSpan?.textContent).toContain("40");
    fireEvent.keyDown(window, { key: "Delete" });
    const roll = document.querySelector('[data-note-count="0"]');
    expect(roll).not.toBeNull();
    expect(roll!.querySelector('[data-note-id="b1"]')).toBeNull();
  });

  it("Backspace inside velocity input does not delete the note", () => {
    render(<MidiEditor songId="s1" />);
    const note = document.querySelector('[data-note-id="b1"]');
    fireEvent.pointerDown(note!);
    const velocityInput = screen.getByLabelText("Velocity 力度");
    fireEvent.change(velocityInput, { target: { value: "100" } });
    // focus is on the input
    fireEvent.keyDown(velocityInput, { key: "Backspace" });
    // note should still exist (1 note remains)
    const roll = document.querySelector('[data-note-count="1"]');
    expect(roll).not.toBeNull();
    expect(roll!.querySelector('[data-note-id="b1"]')).not.toBeNull();
    // velocity updated to 100
    expect(screen.getByLabelText("Velocity 力度")).toHaveValue(100);
  });
});
