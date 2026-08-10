// features/midi/editor/midiEditorLayout.test.ts（T34.3）
// 坐标纯函数：tick→x、duration→width、pitch→row、ticksPerBar（4/4 与 3/4）。

import { describe, expect, it } from "vitest";

import {
  computeMaxTick,
  computePitchRange,
  DEFAULT_LAYOUT,
  pitchToRow,
  rowToY,
  tickToBar,
  tickToBeat,
  tickToWidth,
  tickToX,
  ticksPerBar,
  ticksPerMeterBeat,
  visibleBarCount,
} from "./midiEditorLayout";

describe("coordinate helpers", () => {
  it("tickToX maps tick to pixel", () => {
    expect(tickToX(0, DEFAULT_LAYOUT)).toBe(0);
    expect(tickToX(480, DEFAULT_LAYOUT)).toBeCloseTo(480 * DEFAULT_LAYOUT.pixelsPerTick);
  });

  it("tickToWidth scales duration", () => {
    expect(tickToWidth(480, DEFAULT_LAYOUT)).toBeCloseTo(480 * DEFAULT_LAYOUT.pixelsPerTick);
    expect(tickToWidth(0, DEFAULT_LAYOUT)).toBeGreaterThanOrEqual(2); // min width
  });

  it("pitchToRow gives higher pitch higher row (smaller index)", () => {
    expect(pitchToRow(60, 72)).toBe(12); // 72-60
    expect(pitchToRow(72, 72)).toBe(0);
  });

  it("rowToY scales row", () => {
    expect(rowToY(2, DEFAULT_LAYOUT)).toBe(2 * DEFAULT_LAYOUT.rowHeight);
  });

  it("ticksPerBar respects time signature", () => {
    expect(ticksPerBar(480, { numerator: 4, denominator: 4 })).toBe(1920);
    expect(ticksPerBar(480, { numerator: 3, denominator: 4 })).toBe(1440);
    expect(ticksPerBar(480, { numerator: 6, denominator: 8 })).toBe(1440);
    expect(ticksPerBar(480, { numerator: 2, denominator: 2 })).toBe(1920);
    expect(ticksPerMeterBeat(480, { numerator: 6, denominator: 8 })).toBe(240);
  });

  it("tickToBar is 1-based", () => {
    expect(tickToBar(0, 480, { numerator: 4, denominator: 4 })).toBe(1);
    expect(tickToBar(1920, 480, { numerator: 4, denominator: 4 })).toBe(2);
  });

  it("tickToBeat converts", () => {
    expect(tickToBeat(960, 480)).toBe(2);
  });

  it("visibleBarCount has minimum and extends to maxTick", () => {
    expect(visibleBarCount(0, 480, { numerator: 4, denominator: 4 }, 4)).toBe(4);
    const maxTick = 1920 * 6; // 6 bars
    expect(visibleBarCount(maxTick, 480, { numerator: 4, denominator: 4 })).toBe(6);
  });

  it("computePitchRange pads around notes", () => {
    const { minPitch, maxPitch } = computePitchRange([{ pitch: 40 }, { pitch: 48 }]);
    expect(minPitch).toBeLessThanOrEqual(40);
    expect(maxPitch).toBeGreaterThanOrEqual(48);
  });

  it("computePitchRange returns fallback for empty", () => {
    const { minPitch, maxPitch } = computePitchRange([]);
    expect(minPitch).toBe(48);
    expect(maxPitch).toBe(84);
  });

  it("computeMaxTick is 0 for empty", () => {
    expect(computeMaxTick([])).toBe(0);
    expect(computeMaxTick([{ startTick: 10, durationTick: 20 }])).toBe(30);
  });
});
