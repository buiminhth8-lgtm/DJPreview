// features/midi/editor/midiEditorGeometry.ts（T34.4）
// 指针坐标 ↔ canonical tick/pitch + Snap 纯函数。
// 所有时间均为 integer MIDI tick。

import { DEFAULT_LAYOUT } from "./midiEditorLayout";
import { ticksPerBar } from "./midiEditorLayout";
import type { MeterInfo } from "./midiEditorLayout";

export type SnapValue = "1/1" | "1/2" | "1/4" | "1/8" | "1/16" | "1/32" | "off";

export const SNAP_OPTIONS: SnapValue[] = ["1/1", "1/2", "1/4", "1/8", "1/16", "1/32", "off"];

export const DEFAULT_SNAP: SnapValue = "1/16";

export const DEFAULT_NEW_NOTE_VELOCITY = 90;

const SNAP_DIVISOR: Record<Exclude<SnapValue, "off">, number> = {
  "1/1": 0.25, // quarter = ppq → whole = ppq*4
  "1/2": 0.5,
  "1/4": 1,
  "1/8": 2,
  "1/16": 4,
  "1/32": 8,
};

/** Snap 值 → 一个量化单位的 tick 数。1/1 = 4 * ppq；1/4 = ppq；1/16 = ppq/4。 */
export function getSnapTicks(snap: SnapValue, ppq: number): number {
  if (snap === "off") return 1;
  const divisor = SNAP_DIVISOR[snap];
  const ticks = Math.max(1, Math.round((ppq * 4) / (divisor * 4)));
  return Math.max(1, ticks);
}

/** 把 tick 量化到最近的 snap 网格（integer）。Snap off 时返回 round(tick)。 */
export function snapTick(tick: number, snap: SnapValue, ppq: number): number {
  const unit = getSnapTicks(snap, ppq);
  return Math.max(0, Math.round(tick / unit) * unit);
}

/** 鼠标 x（相对 grid 内容）→ tick。scroll 由 getBoundingClientRect + scrollLeft 已在调用方扣除。 */
export function xToTick(relativeX: number, pixelsPerTick: number, ppq: number, snap: SnapValue): number {
  const raw = Math.max(0, relativeX / pixelsPerTick);
  const tick = Math.round(raw);
  return snapTick(tick, snap, ppq);
}

/** 鼠标 y（相对 grid 内容）→ pitch。maxPitch 顶部。 */
export function yToPitch(relativeY: number, rowHeight: number, maxPitch: number): number {
  const row = Math.floor(relativeY / Math.max(1, rowHeight));
  const pitch = maxPitch - row;
  return Math.max(0, Math.min(127, pitch));
}

/** pointer 坐标（相对 editor 容器）→ grid 内容相对坐标（扣除键盘宽度 + 滚动）。 */
export function toGridRelative(
  clientX: number,
  clientY: number,
  rect: DOMRect,
  scrollLeft: number,
  scrollTop: number,
  keyboardWidth: number,
): { x: number; y: number } {
  const x = clientX - rect.left - keyboardWidth + scrollLeft;
  const y = clientY - rect.top + scrollTop;
  return { x, y };
}

/** resize 时：endTick = startTick + durationTick；snap endTick 后反推 duration。 */
export function snapResizeEnd(
  startTick: number,
  newDurationTick: number,
  snap: SnapValue,
  ppq: number,
): number {
  const endTick = snapTick(startTick + newDurationTick, snap, ppq);
  return Math.max(1, endTick - startTick);
}

export function midiPitchToNoteName(pitch: number): string {
  const names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
  const name = names[pitch % 12];
  const octave = Math.floor(pitch / 12) - 1;
  return `${name}${octave}`;
}

/** 整个 document/song 的 maxTick（跨轨道，供 Timeline 稳定长度）。 */
export function documentMaxTick(
  tracks: Array<{ notes: Array<{ startTick: number; durationTick: number }> }>,
): number {
  let max = 0;
  for (const track of tracks) {
    for (const n of track.notes) {
      const end = n.startTick + n.durationTick;
      if (end > max) max = end;
    }
  }
  return max;
}

export function defaultPitchRangeForChannel(channel: number): { minPitch: number; maxPitch: number } {
  // drum → kick..high hat 区（36-60）；其他 → C2..C6
  if (channel === 9) return { minPitch: 36, maxPitch: 60 };
  return { minPitch: 48, maxPitch: 84 };
}

export { ticksPerBar, DEFAULT_LAYOUT, MeterInfo };
