// features/midi/editor/midiEditorGeometry.test.ts（T34.4）
// Snap 换算（PPQ=480 与其它 PPQ）+ 坐标映射 + 音符名。

import { describe, expect, it } from "vitest";

import {
  DEFAULT_SNAP,
  getSnapTicks,
  midiPitchToNoteName,
  snapResizeEnd,
  snapTick,
  toGridRelative,
  xToTick,
  yToPitch,
} from "./midiEditorGeometry";

describe("snap tick conversion", () => {
  it("PPQ=480 maps note divisions", () => {
    expect(getSnapTicks("1/1", 480)).toBe(1920);
    expect(getSnapTicks("1/2", 480)).toBe(960);
    expect(getSnapTicks("1/4", 480)).toBe(480);
    expect(getSnapTicks("1/8", 480)).toBe(240);
    expect(getSnapTicks("1/16", 480)).toBe(120);
    expect(getSnapTicks("1/32", 480)).toBe(60);
    expect(getSnapTicks("off", 480)).toBe(1);
  });

  it("respects other PPQ (960)", () => {
    expect(getSnapTicks("1/4", 960)).toBe(960);
    expect(getSnapTicks("1/16", 960)).toBe(240);
  });

  it("handles non-divisible PPQ deterministically (1200)", () => {
    // 1200 / 8 = 150 (1/32)；1/16 = 1200/4=300
    expect(getSnapTicks("1/32", 1200)).toBe(150);
    expect(getSnapTicks("1/16", 1200)).toBe(300);
  });

  it("snapTick quantizes to grid", () => {
    expect(snapTick(125, "1/16", 480)).toBe(120); // nearest 120
    expect(snapTick(60, "1/16", 480)).toBe(120); // round(0.5)=1 → 120
    expect(snapTick(100, "1/16", 480)).toBe(120);
    expect(snapTick(10, "off", 480)).toBe(10); // off keeps integer
  });
});

describe("coordinate mapping", () => {
  it("xToTick converts pixel to snapped tick", () => {
    // pixelsPerTick=0.4 → 120px = 300 raw tick → snap 1/16 (120) → round(2.5)=3 → 360
    expect(xToTick(120, 0.4, 480, "1/16")).toBe(360);
  });

  it("yToPitch maps row to pitch with maxPitch on top", () => {
    expect(yToPitch(0, 12, 72)).toBe(72);
    expect(yToPitch(12, 12, 72)).toBe(71);
    expect(yToPitch(1000, 12, 72)).toBe(0); // clamp
    // floor(-5/12) = -1 → pitch = 72-(-1)=73 → clamp 73 (within 0..127)
    expect(yToPitch(-5, 12, 72)).toBe(73);
  });

  it("toGridRelative accounts for keyboard width and scroll", () => {
    const { x, y } = toGridRelative(200, 150, { left: 100, top: 50 } as DOMRect, 300, 20, 56);
    expect(x).toBe(200 - 100 - 56 + 300);
    expect(y).toBe(150 - 50 + 20);
  });

  it("snapResizeEnd snaps the end tick", () => {
    // start=0, dur=130 → end=130 → snap 1/16 (120) → 120 → dur=120
    expect(snapResizeEnd(0, 130, "1/16", 480)).toBe(120);
  });

  it("note name uses C4 convention", () => {
    expect(midiPitchToNoteName(60)).toBe("C4");
    expect(midiPitchToNoteName(36)).toBe("C2");
    expect(midiPitchToNoteName(61)).toBe("C#4");
  });

  it("default snap is 1/16", () => {
    expect(DEFAULT_SNAP).toBe("1/16");
  });
});
