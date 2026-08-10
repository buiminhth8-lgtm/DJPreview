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
  selectedNoteIds: new Set<string>(),
  onSelectNotes: vi.fn(),
  onAddNote: vi.fn(),
  onMoveNotes: vi.fn(),
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
    expect(baseProps.onSelectNotes).toHaveBeenCalledWith(["n1"], "replace");
  });

  it("pointermove with delta triggers onMoveNote with canonical tick/pitch", () => {
    const move = vi.fn();
    render(
      <div style={{ width: 800, height: 300 }}>
        <PianoRollViewport {...baseProps} notes={oneNote} onMoveNotes={move} />
      </div>,
    );
    const g = document.querySelector('[data-note-id="n1"]')!;
    fireEvent.pointerDown(g, { pointerId: 1, clientX: 100, clientY: 100 });
    // drag right 120px (0.4 px/tick → 300 raw → snap 1/16(120) → 240) and up 1 row (12px)
    fireEvent.pointerMove(g, { pointerId: 1, clientX: 220, clientY: 88 });
    fireEvent.pointerUp(g, { pointerId: 1 });
    expect(move).toHaveBeenCalled();
    const [changes] = move.mock.calls[0];
    expect(changes[0].id).toBe("n1");
    expect(changes[0].startTick).toBeGreaterThan(0);
    expect(changes[0].pitch).toBe(61); // 60 + 1 semitone up
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

  it("Ctrl/Cmd click toggles a note and Shift click appends", () => {
    const select = vi.fn();
    render(
      <PianoRollViewport
        {...baseProps}
        notes={oneNote}
        selectedNoteIds={new Set(["n1"])}
        onSelectNotes={select}
      />,
    );
    const note = document.querySelector('[data-note-id="n1"]')!;
    fireEvent.pointerDown(note, { pointerId: 3, ctrlKey: true });
    expect(select).toHaveBeenCalledWith(["n1"], "toggle");
    fireEvent.pointerDown(note, { pointerId: 4, shiftKey: true });
    expect(select).toHaveBeenCalledWith(["n1"], "append");
  });

  it("empty-grid drag reports a box selection and supports toggle intent", () => {
    const select = vi.fn();
    render(
      <PianoRollViewport {...baseProps} notes={oneNote} onSelectNotes={select} />,
    );
    const svg = document.querySelector(".midi-editor__roll")!;
    const grid = document.querySelector(".midi-editor__grid")!;
    fireEvent.pointerDown(svg, { pointerId: 5, clientX: 0, clientY: 0, ctrlKey: true });
    fireEvent.pointerMove(grid, { pointerId: 5, clientX: 210, clientY: 60, ctrlKey: true });
    expect(document.querySelector('[data-testid="selection-box"]')).not.toBeNull();
    fireEvent.pointerUp(grid, { pointerId: 5, clientX: 210, clientY: 60, ctrlKey: true });
    expect(select).toHaveBeenLastCalledWith(["n1"], "toggle");
  });

  it("box selection stays correct after horizontal/vertical zoom and scroll", () => {
    const select = vi.fn();
    const zoomedLayout = { pixelsPerTick: 0.8, rowHeight: 24, keyboardWidth: 72 };
    render(
      <PianoRollViewport
        {...baseProps}
        notes={[{ ...oneNote[0], startTick: 240 }]}
        layout={zoomedLayout}
        onSelectNotes={select}
      />,
    );
    const grid = document.querySelector(".midi-editor__grid") as HTMLDivElement;
    const svg = document.querySelector(".midi-editor__roll")!;
    Object.defineProperty(grid, "scrollLeft", { value: 100, writable: true });
    Object.defineProperty(grid, "scrollTop", { value: 24, writable: true });
    vi.spyOn(grid, "getBoundingClientRect").mockReturnValue({
      left: 10,
      top: 20,
      right: 810,
      bottom: 320,
      width: 800,
      height: 300,
      x: 10,
      y: 20,
      toJSON: () => ({}),
    });
    fireEvent.pointerDown(svg, { pointerId: 8, clientX: 90, clientY: 60 });
    fireEvent.pointerMove(grid, { pointerId: 8, clientX: 160, clientY: 90 });
    fireEvent.pointerUp(grid, { pointerId: 8, clientX: 160, clientY: 90 });
    expect(select).toHaveBeenLastCalledWith(["n1"], "replace");
  });

  it("dragging one selected note moves the full group with uniform deltas", () => {
    const move = vi.fn();
    const group = [
      ...oneNote,
      { id: "n2", pitch: 64, startTick: 480, durationTick: 240, velocity: 90, channel: 0 },
    ];
    render(
      <PianoRollViewport
        {...baseProps}
        notes={group}
        selectedNoteIds={new Set(["n1", "n2"])}
        onMoveNotes={move}
      />,
    );
    expect(document.querySelectorAll(".midi-editor__resize")).toHaveLength(0);
    const note = document.querySelector('[data-note-id="n1"]')!;
    fireEvent.pointerDown(note, { pointerId: 6, clientX: 100, clientY: 100 });
    fireEvent.pointerMove(note, { pointerId: 6, clientX: 220, clientY: 88 });
    const changes = move.mock.calls[0][0];
    expect(changes).toHaveLength(2);
    expect(changes[1].startTick - changes[0].startTick).toBe(480);
    expect(changes[1].pitch - changes[0].pitch).toBe(4);
  });

  it("locked track still selects but blocks move and add", () => {
    const select = vi.fn();
    const move = vi.fn();
    const add = vi.fn();
    render(
      <PianoRollViewport
        {...baseProps}
        notes={oneNote}
        locked
        onSelectNotes={select}
        onMoveNotes={move}
        onAddNote={add}
      />,
    );
    const note = document.querySelector('[data-note-id="n1"]')!;
    fireEvent.pointerDown(note, { pointerId: 7, clientX: 100, clientY: 100 });
    fireEvent.pointerMove(note, { pointerId: 7, clientX: 220, clientY: 88 });
    expect(select).toHaveBeenCalledWith(["n1"], "replace");
    expect(move).not.toHaveBeenCalled();
    fireEvent.doubleClick(document.querySelector(".midi-editor__grid")!, { clientX: 50, clientY: 50 });
    expect(add).not.toHaveBeenCalled();
  });
});
