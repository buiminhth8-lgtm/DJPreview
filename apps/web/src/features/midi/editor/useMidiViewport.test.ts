// features/midi/editor/useMidiViewport.test.ts（T34.5）
// zoom limits、zoom 不改 canonical ticks、fit（含 empty）、reset。

import { describe, expect, it } from "vitest";
import { act, renderHook } from "@testing-library/react";

import {
  MAX_HORIZONTAL_ZOOM,
  MAX_ROW_HEIGHT,
  MIN_HORIZONTAL_ZOOM,
  MIN_ROW_HEIGHT,
  useMidiViewport,
} from "./useMidiViewport";
import { DEFAULT_LAYOUT } from "./midiEditorLayout";

const DEFAULT_PPT = DEFAULT_LAYOUT.pixelsPerTick;
const DEFAULT_RH = DEFAULT_LAYOUT.rowHeight;

describe("useMidiViewport", () => {
  it("horizontal zoom changes pixelsPerTick, not canonical ticks", () => {
    const { result } = renderHook(() => useMidiViewport());
    act(() => result.current.zoomHIn());
    expect(result.current.pixelsPerTick).toBeGreaterThan(DEFAULT_PPT);
    act(() => result.current.zoomHOut());
    act(() => result.current.zoomHOut());
    expect(result.current.pixelsPerTick).toBeLessThan(DEFAULT_PPT);
    // min clamp
    for (let i = 0; i < 50; i += 1) act(() => result.current.zoomHOut());
    expect(result.current.pixelsPerTick).toBeGreaterThanOrEqual(MIN_HORIZONTAL_ZOOM * DEFAULT_PPT);
    // max clamp
    for (let i = 0; i < 50; i += 1) act(() => result.current.zoomHIn());
    expect(result.current.pixelsPerTick).toBeLessThanOrEqual(MAX_HORIZONTAL_ZOOM * DEFAULT_PPT);
  });

  it("vertical zoom changes rowHeight only", () => {
    const { result } = renderHook(() => useMidiViewport());
    act(() => result.current.zoomVIn());
    expect(result.current.rowHeight).toBe(DEFAULT_RH + 2);
    act(() => result.current.zoomVOut());
    act(() => result.current.zoomVOut());
    expect(result.current.rowHeight).toBeLessThan(DEFAULT_RH);
    for (let i = 0; i < 50; i += 1) act(() => result.current.zoomVOut());
    expect(result.current.rowHeight).toBeGreaterThanOrEqual(MIN_ROW_HEIGHT);
    for (let i = 0; i < 50; i += 1) act(() => result.current.zoomVIn());
    expect(result.current.rowHeight).toBeLessThanOrEqual(MAX_ROW_HEIGHT);
  });

  it("resetZoom restores defaults", () => {
    const { result } = renderHook(() => useMidiViewport());
    act(() => result.current.zoomHIn());
    act(() => result.current.zoomVIn());
    act(() => result.current.resetZoom());
    expect(result.current.pixelsPerTick).toBe(DEFAULT_PPT);
    expect(result.current.rowHeight).toBe(DEFAULT_RH);
  });

  it("horizontalPercent reflects zoom", () => {
    const { result } = renderHook(() => useMidiViewport());
    expect(result.current.horizontalPercent).toBe(100);
    act(() => result.current.zoomHIn());
    expect(result.current.horizontalPercent).toBeGreaterThan(100);
  });

  it("fitTrack fits notes within min/max zoom and sets scroll", () => {
    const { result } = renderHook(() => useMidiViewport());
    act(() =>
      result.current.fitTrack(
        [
          { pitch: 40, startTick: 0, durationTick: 480 },
          { pitch: 52, startTick: 480 * 8, durationTick: 960 },
        ],
        480,
        { numerator: 4, denominator: 4 },
        800,
        300,
      ),
    );
    expect(result.current.pixelsPerTick).toBeGreaterThanOrEqual(MIN_HORIZONTAL_ZOOM * DEFAULT_PPT);
    expect(result.current.pixelsPerTick).toBeLessThanOrEqual(MAX_HORIZONTAL_ZOOM * DEFAULT_PPT);
    expect(result.current.rowHeight).toBeGreaterThanOrEqual(MIN_ROW_HEIGHT);
    expect(result.current.rowHeight).toBeLessThanOrEqual(MAX_ROW_HEIGHT);
    expect(Number.isFinite(result.current.scrollLeft)).toBe(true);
    expect(Number.isFinite(result.current.scrollTop)).toBe(true);
  });

  it("fitTrack empty does not fail and uses sane defaults", () => {
    const { result } = renderHook(() => useMidiViewport());
    act(() => result.current.fitTrack([], 480, { numerator: 4, denominator: 4 }, 800, 300));
    expect(Number.isFinite(result.current.pixelsPerTick)).toBe(true);
    expect(Number.isFinite(result.current.rowHeight)).toBe(true);
    expect(result.current.rowHeight).toBeGreaterThanOrEqual(MIN_ROW_HEIGHT);
    expect(result.current.scrollLeft).toBe(0);
    expect(result.current.scrollTop).toBe(0);
  });

  it("single short note fit is bounded (not full screen)", () => {
    const { result } = renderHook(() => useMidiViewport());
    act(() => result.current.fitTrack([{ pitch: 60, startTick: 0, durationTick: 120 }], 480, { numerator: 4, denominator: 4 }, 800, 300));
    // must be <= max zoom so one note doesn't fill screen
    expect(result.current.pixelsPerTick).toBeLessThanOrEqual(MAX_HORIZONTAL_ZOOM * DEFAULT_PPT);
  });
});
