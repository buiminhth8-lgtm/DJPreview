// features/midi/editor/PianoRollViewport.test.tsx（T34.3/34.4）
// 空轨道显示 + 音符渲染（note.id key）。

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { PianoRollViewport } from "./PianoRollViewport";

const baseProps = {
  ppq: 480,
  meter: { numerator: 4, denominator: 4 } as const,
  bpm: 120,
  channel: 0,
  isDrum: false,
  snap: "1/16" as const,
  selectedNoteId: null,
  onSelectNote: vi.fn(),
  onAddNote: vi.fn(),
  onMoveNote: vi.fn(),
  onResizeNote: vi.fn(),
};

describe("PianoRollViewport", () => {
  it("shows empty-track message when notes empty", () => {
    render(<PianoRollViewport {...baseProps} notes={[]} />);
    expect(screen.getByText(/当前轨道没有音符/)).toBeInTheDocument();
    expect(screen.getByText(/0 notes/)).toBeInTheDocument();
  });

  it("renders notes with note.id keys via data attribute", () => {
    render(
      <PianoRollViewport
        {...baseProps}
        notes={[{ id: "x1", pitch: 60, startTick: 0, durationTick: 480, velocity: 100, channel: 0 }]}
      />,
    );
    const note = document.querySelector('[data-note-id="x1"]');
    expect(note).not.toBeNull();
    expect(screen.getByText(/1 notes/)).toBeInTheDocument();
  });
});
