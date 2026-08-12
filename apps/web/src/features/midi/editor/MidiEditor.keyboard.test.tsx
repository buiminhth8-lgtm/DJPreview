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
    {
      id: "drums",
      role: "drums",
      name: "drums",
      channel: 9,
      instrument: null,
      isDrum: true,
      notes: [{ id: "d1", pitch: 36, startTick: 0, durationTick: 120, velocity: 100, channel: 9 }],
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
  const editor = () => document.querySelector(".midi-editor")!;

  it("Delete removes the selected note", () => {
    render(<MidiEditor songId="s1" />);
    // select bass note b1 by clicking its rect
    const note = document.querySelector('[data-note-id="b1"]');
    fireEvent.pointerDown(note!);
    // note 40 = E2; footer text may be split across nodes → check textContent
    const selectedSpan = document.querySelector(".midi-editor__selected-note");
    expect(selectedSpan?.textContent).toContain("E2");
    expect(selectedSpan?.textContent).toContain("40");
    fireEvent.keyDown(editor(), { key: "Delete" });
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

  it("select all, internal copy/paste, duplicate, undo/redo and batch delete stay in draft history", () => {
    render(<MidiEditor songId="s1" />);
    fireEvent.pointerDown(document.querySelector('[data-note-id="b1"]')!);
    fireEvent.keyDown(editor(), { key: "a", ctrlKey: true });
    expect(screen.getByTestId("selected-note-count")).toHaveTextContent("Selected: 1");

    fireEvent.keyDown(editor(), { key: "c", ctrlKey: true });
    expect(document.querySelector('[data-note-count="1"]')).not.toBeNull();
    expect(screen.queryByText("未保存草稿")).not.toBeInTheDocument();

    fireEvent.keyDown(editor(), { key: "v", ctrlKey: true });
    expect(document.querySelector('[data-note-count="2"]')).not.toBeNull();
    expect(screen.getByTestId("selected-note-count")).toHaveTextContent("Selected: 1");
    fireEvent.keyDown(editor(), { key: "z", ctrlKey: true });
    expect(document.querySelector('[data-note-count="1"]')).not.toBeNull();
    fireEvent.keyDown(editor(), { key: "y", ctrlKey: true });
    expect(document.querySelector('[data-note-count="2"]')).not.toBeNull();

    fireEvent.pointerDown(document.querySelector('[data-note-id="b1"]')!);
    fireEvent.keyDown(editor(), { key: "d", ctrlKey: true });
    expect(document.querySelector('[data-note-count="3"]')).not.toBeNull();
    fireEvent.keyDown(editor(), { key: "a", ctrlKey: true });
    fireEvent.keyDown(editor(), { key: "Delete" });
    expect(document.querySelector('[data-note-count="0"]')).not.toBeNull();
    fireEvent.keyDown(editor(), { key: "z", ctrlKey: true });
    expect(document.querySelector('[data-note-count="3"]')).not.toBeNull();
  });

  it("rejects drum-to-pitched clipboard paste with a clear message", () => {
    render(<MidiEditor songId="s1" />);
    fireEvent.pointerDown(document.querySelector('[data-note-id="b1"]')!);
    fireEvent.keyDown(editor(), { key: "c", ctrlKey: true });
    fireEvent.click(screen.getByRole("option", { name: /drums/ }));
    fireEvent.keyDown(editor(), { key: "v", ctrlKey: true });
    expect(screen.getByText("鼓组轨与有调轨之间不能直接粘贴音符")).toBeInTheDocument();
    expect(document.querySelector('[data-note-count="1"]')).not.toBeNull();
  });

  it("Esc and track changes clear current-track selection", () => {
    render(<MidiEditor songId="s1" />);
    fireEvent.pointerDown(document.querySelector('[data-note-id="b1"]')!);
    expect(screen.getByTestId("selected-note-count")).toHaveTextContent("Selected: 1");
    fireEvent.keyDown(editor(), { key: "Escape" });
    expect(screen.getByTestId("selected-note-count")).toHaveTextContent("Selected: 0");
    fireEvent.pointerDown(document.querySelector('[data-note-id="b1"]')!);
    fireEvent.click(screen.getByRole("option", { name: /melody/ }));
    expect(screen.getByTestId("selected-note-count")).toHaveTextContent("Selected: 0");
  });

  it("locked track allows Copy but blocks Paste and Duplicate", () => {
    render(<MidiEditor songId="s1" />);
    fireEvent.pointerDown(document.querySelector('[data-note-id="b1"]')!);
    fireEvent.click(screen.getByRole("button", { name: /编辑/ }));
    fireEvent.keyDown(editor(), { key: "c", ctrlKey: true });
    expect(screen.getByText("已复制 1 个音符")).toBeInTheDocument();
    fireEvent.keyDown(editor(), { key: "v", ctrlKey: true });
    expect(screen.getByText("当前轨道已锁定，不能粘贴")).toBeInTheDocument();
    fireEvent.keyDown(editor(), { key: "d", ctrlKey: true });
    expect(screen.getByText("当前轨道已锁定，不能复制音符")).toBeInTheDocument();
    expect(document.querySelector('[data-note-count="1"]')).not.toBeNull();
  });

  it("reports dirty state to the Workspace guard and clears it on unmount", () => {
    const onDirtyChange = vi.fn();
    const { unmount } = render(<MidiEditor songId="s1" onDirtyChange={onDirtyChange} />);
    expect(onDirtyChange).toHaveBeenLastCalledWith(false);

    fireEvent.pointerDown(document.querySelector('[data-note-id="b1"]')!);
    fireEvent.keyDown(editor(), { key: "Delete" });
    expect(onDirtyChange).toHaveBeenLastCalledWith(true);

    unmount();
    expect(onDirtyChange).toHaveBeenLastCalledWith(false);
  });
});
