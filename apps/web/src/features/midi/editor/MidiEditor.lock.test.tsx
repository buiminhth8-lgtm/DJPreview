// features/midi/editor/MidiEditor.lock.test.tsx（T34.5）
// Track Lock：阻止 Add/Delete/Move/Resize/Velocity；保留 Draft；允许选择/pan/zoom。

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

function lockToggle() {
  return screen.getByRole("button", { name: /锁定|编辑/ });
}

describe("MidiEditor track lock", () => {
  it("default is unlocked (editable)", () => {
    render(<MidiEditor songId="s1" />);
    expect(lockToggle()).toHaveTextContent("🔓 编辑");
  });

  it("locking blocks Delete and preserves note", () => {
    render(<MidiEditor songId="s1" />);
    // select note
    const note = document.querySelector('[data-note-id="b1"]');
    fireEvent.pointerDown(note!);
    // lock
    fireEvent.click(lockToggle());
    expect(lockToggle()).toHaveTextContent("🔒 已锁定");
    // Delete should NOT remove
    fireEvent.keyDown(window, { key: "Delete" });
    const roll = document.querySelector('[data-note-count="1"]');
    expect(roll).not.toBeNull();
    expect(roll!.querySelector('[data-note-id="b1"]')).not.toBeNull();
  });

  it("locking blocks velocity edit", () => {
    render(<MidiEditor songId="s1" />);
    const note = document.querySelector('[data-note-id="b1"]');
    fireEvent.pointerDown(note!);
    const velocityInput = screen.getByLabelText("Velocity 力度");
    fireEvent.change(velocityInput, { target: { value: "50" } });
    // unlocked: velocity updates
    expect(velocityInput).toHaveValue(50);

    // lock → change should not apply
    fireEvent.click(lockToggle());
    fireEvent.change(velocityInput, { target: { value: "60" } });
    // velocity input is disabled/read-only when locked
    expect(velocityInput).toBeDisabled();
  });

  it("locking preserves existing draft", () => {
    render(<MidiEditor songId="s1" />);
    // modify velocity while unlocked (creates dirty draft)
    const note = document.querySelector('[data-note-id="b1"]');
    fireEvent.pointerDown(note!);
    const velocityInput = screen.getByLabelText("Velocity 力度");
    fireEvent.change(velocityInput, { target: { value: "77" } });
    expect(velocityInput).toHaveValue(77);
    // lock then unlock
    fireEvent.click(lockToggle());
    fireEvent.click(lockToggle());
    const velocityAfter = screen.getByLabelText("Velocity 力度");
    expect(velocityAfter).toHaveValue(77); // draft preserved
  });
});
