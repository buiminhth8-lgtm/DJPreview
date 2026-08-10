// features/midi/editor/PianoRollViewport.test.tsx（T34.3）
// 空轨道显示 + 只读（无编辑交互）。

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { PianoRollViewport } from "./PianoRollViewport";

describe("PianoRollViewport", () => {
  it("shows empty-track message when notes empty", () => {
    render(
      <PianoRollViewport
        notes={[]}
        ppq={480}
        meter={{ numerator: 4, denominator: 4 }}
        bpm={120}
        selectedNoteId={null}
        onSelectNote={() => undefined}
      />,
    );
    expect(screen.getByText("当前轨道没有音符")).toBeInTheDocument();
    expect(screen.getByText(/0 notes/)).toBeInTheDocument();
  });

  it("renders notes with note.id keys via data attribute", () => {
    render(
      <PianoRollViewport
        notes={[{ id: "x1", pitch: 60, startTick: 0, durationTick: 480, velocity: 100, channel: 0 }]}
        ppq={480}
        meter={{ numerator: 4, denominator: 4 }}
        bpm={120}
        selectedNoteId={null}
        onSelectNote={() => undefined}
      />,
    );
    const note = document.querySelector('[data-note-id="x1"]');
    expect(note).not.toBeNull();
    expect(screen.getByText(/1 notes/)).toBeInTheDocument();
  });
});
