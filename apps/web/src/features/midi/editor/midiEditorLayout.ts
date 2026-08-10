// features/midi/editor/midiEditorLayout.ts（T34.3）
// 纯函数：PPQ / 时间 → 像素、pitch → 行。全部基于 canonical integer tick。

export interface MidiEditorLayoutConfig {
  pixelsPerTick: number;
  rowHeight: number; // px per pitch row
  keyboardWidth: number; // px（左侧琴键）
}

export const DEFAULT_LAYOUT: MidiEditorLayoutConfig = {
  pixelsPerTick: 0.4, // 480ppq → 每拍 ~192px，每小节 ~768px
  rowHeight: 12,
  keyboardWidth: 92,
};

export interface MeterInfo {
  numerator: number;
  denominator: number;
}

export function ticksPerBeat(ppq: number): number {
  return Math.max(1, ppq);
}

/** 拍号中一个 denominator 拍的 tick 数（例如 6/8 的八分音符 = ppq/2）。 */
export function ticksPerMeterBeat(ppq: number, meter: MeterInfo): number {
  return Math.max(1, Math.round((Math.max(1, ppq) * 4) / Math.max(1, meter.denominator)));
}

/** 每小节 tick 数：numerator × denominator beat，支持非 4/4。 */
export function ticksPerBar(ppq: number, meter: MeterInfo): number {
  return Math.max(1, meter.numerator) * ticksPerMeterBeat(ppq, meter);
}

export function tickToX(tick: number, layout: MidiEditorLayoutConfig): number {
  return tick * layout.pixelsPerTick;
}

export function tickToWidth(durationTick: number, layout: MidiEditorLayoutConfig): number {
  return Math.max(2, durationTick * layout.pixelsPerTick);
}

/** pitch → 可视行号（0 为顶部）。higher pitch → higher row（视觉上方）。 */
export function pitchToRow(pitch: number, maxPitch: number): number {
  return Math.max(0, maxPitch - pitch);
}

/** row → y（像素）。 */
export function rowToY(row: number, layout: MidiEditorLayoutConfig): number {
  return row * layout.rowHeight;
}

/** 从当前 Track notes 计算 pitch range（带 padding），保证 fit。 */
export function computePitchRange(
  notes: Array<{ pitch: number }>,
  fallbackLow = 48,
  fallbackHigh = 84,
): { minPitch: number; maxPitch: number } {
  if (!notes.length) {
    return { minPitch: fallbackLow, maxPitch: fallbackHigh };
  }
  const min = Math.min(...notes.map((n) => n.pitch));
  const max = Math.max(...notes.map((n) => n.pitch));
  const pad = Math.max(3, Math.ceil((max - min) * 0.25));
  return {
    minPitch: Math.max(0, min - pad),
    maxPitch: Math.min(127, max + pad),
  };
}

/** 从 Track notes 计算最大结束 tick（用于横向 fit）。 */
export function computeMaxTick(notes: Array<{ startTick: number; durationTick: number }>): number {
  if (!notes.length) return 0;
  return Math.max(...notes.map((n) => n.startTick + n.durationTick));
}

/** bar 编号（1-based）：tick → bar。 */
export function tickToBar(tick: number, ppq: number, meter: MeterInfo): number {
  const perBar = ticksPerBar(ppq, meter);
  return Math.floor(tick / perBar) + 1;
}

/** 当前工程实际可渲染的总小节数（由 maxTick 推出，至少 1）。 */
export function visibleBarCount(
  maxTick: number,
  ppq: number,
  meter: MeterInfo,
  minBars = 4,
): number {
  const perBar = ticksPerBar(ppq, meter);
  if (maxTick <= 0) return minBars;
  return Math.max(minBars, Math.ceil(maxTick / perBar));
}

export function tickToBeat(tick: number, ppq: number): number {
  return tick / Math.max(1, ppq);
}
