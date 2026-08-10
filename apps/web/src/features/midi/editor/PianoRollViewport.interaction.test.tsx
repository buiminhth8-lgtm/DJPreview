// features/midi/editor/PianoRollViewport.interaction.test.tsx（T34.4）
// 交互：双击添加、拖移动、右边缘 resize、拖动会更新 canonical draft 字段。

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";

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

const oneNote = [{ id: "n1", pitch: 60, startTick: 0, durationTick: 480, velocity: 100, channel: 0 }];

function renderViewport() {
  return render(
    <div style={{ width: 800, height: 300 }}>
      <PianoRollViewport {...baseProps} notes={oneNote} />
    </div>,
  );
}

describe("PianoRollViewport interaction", () => {
  it("pointerdown on note selects it", () => {
    renderViewport();
    const g = document.querySelector('[data-note-id="n1"]');
    fireEvent.pointerDown(g!);
    expect(baseProps.onSelectNote).toHaveBeenCalledWith("n1");
  });

  it("pointermove with delta triggers onMoveNote with canonical tick/pitch", () => {
    const move = vi.fn();
    render(
      <div style={{ width: 800, height: 300 }}>
        <PianoRollViewport {...baseProps} notes={oneNote} onMoveNote={move} />
      </div>,
    );
    const g = document.querySelector('[data-note-id="n1"]')!;
    fireEvent.pointerDown(g, { pointerId: 1, clientX: 100, clientY: 100 });
    // drag right 120px (0.4 px/tick → 300 raw → snap 1/16(120) → 240) and up 1 row (12px)
    fireEvent.pointerMove(g, { pointerId: 1, clientX: 220, clientY: 88 });
    fireEvent.pointerUp(g, { pointerId: 1 });
    expect(move).toHaveBeenCalled();
    const [noteId, startTick, pitch] = move.mock.calls[0];
    expect(noteId).toBe("n1");
    expect(startTick).toBeGreaterThan(0);
    expect(pitch).toBe(61); // 60 + 1 semitone up
  });

  it("resize handle drag changes duration not start", () => {
    const resize = vi.fn();
    render(
      <div style={{ width: 800, height: 300 }}>
        <PianoRollViewport {...baseProps} notes={oneNote} onResizeNote={resize} />
      </div>,
    );
    // note width = 480*0.4=192; resize handle at x = note.x + width - 6
    const g = document.querySelector('[data-note-id="n1"]')!;
    const resizeHandle = g.querySelector(".midi-editor__resize")!;
    fireEvent.pointerDown(resizeHandle, { pointerId: 2, clientX: 200, clientY: 100 });
    fireEvent.pointerMove(resizeHandle, { pointerId: 2, clientX: 320, clientY: 100 });
    fireEvent.pointerUp(resizeHandle, { pointerId: 2 });
    expect(resize).toHaveBeenCalled();
    const [noteId, duration] = resize.mock.calls[0];
    expect(noteId).toBe("n1");
    expect(duration).toBeGreaterThan(480);
  });

  it("double-click empty grid adds a note", () => {
    const add = vi.fn();
    render(
      <div style={{ width: 800, height: 300 }}>
        <PianoRollViewport {...baseProps} notes={oneNote} onAddNote={add} />
      </div>,
    );
    const grid = document.querySelector(".midi-editor__grid")!;
    // click around tick 480*2=960px → x=960? but grid is small; use a position near left
    fireEvent.doubleClick(grid, { clientX: 50, clientY: 50 });
    expect(add).toHaveBeenCalled();
    const note = add.mock.calls[0][0];
    expect(note.pitch).toBeGreaterThanOrEqual(0);
    expect(note.startTick).toBeGreaterThanOrEqual(0);
    expect(note.durationTick).toBeGreaterThan(0);
    expect(note.velocity).toBeGreaterThanOrEqual(1);
    expect(note.velocity).toBeLessThanOrEqual(127);
    expect(note.channel).toBe(0);
  });
});
