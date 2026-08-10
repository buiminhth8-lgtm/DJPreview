// features/midi/editor/useMidiViewport.ts（T34.5）
// 视口状态：horizontal/vertical zoom + scroll + fit。
// 只影响视觉映射（pixelsPerTick / rowHeight / scroll），绝不修改 canonical MIDI 数据。

import { useCallback, useEffect, useState } from "react";
import { DEFAULT_LAYOUT } from "./midiEditorLayout";
import { ticksPerBar } from "./midiEditorLayout";

export const MIN_HORIZONTAL_ZOOM = 0.25;
export const MAX_HORIZONTAL_ZOOM = 4;
export const MIN_ROW_HEIGHT = 6;
export const MAX_ROW_HEIGHT = 28;
export const DEFAULT_ROW_HEIGHT = DEFAULT_LAYOUT.rowHeight;
export const DEFAULT_PIXELS_PER_TICK = DEFAULT_LAYOUT.pixelsPerTick;

export interface UseMidiViewportResult {
  pixelsPerTick: number;
  rowHeight: number;
  scrollLeft: number;
  scrollTop: number;
  setScrollLeft: (v: number) => void;
  setScrollTop: (v: number) => void;
  zoomHIn: () => void;
  zoomHOut: () => void;
  zoomVIn: () => void;
  zoomVOut: () => void;
  resetZoom: () => void;
  horizontalPercent: number;
  fitTrack: (
    notes: Array<{ pitch: number; startTick: number; durationTick: number }>,
    ppq: number,
    meter: { numerator: number; denominator: number },
    containerWidth: number,
    containerHeight: number,
  ) => void;
}

export function useMidiViewport(): UseMidiViewportResult {
  const [pixelsPerTick, setPixelsPerTick] = useState(DEFAULT_PIXELS_PER_TICK);
  const [rowHeight, setRowHeight] = useState(DEFAULT_ROW_HEIGHT);
  const [scrollLeft, setScrollLeft] = useState(0);
  const [scrollTop, setScrollTop] = useState(0);

  // 100% = DEFAULT_PIXELS_PER_TICK
  const horizontalPercent = Math.round((pixelsPerTick / DEFAULT_PIXELS_PER_TICK) * 100);

  const zoomHIn = useCallback(() => {
    setPixelsPerTick((p) => Math.min(MAX_HORIZONTAL_ZOOM * DEFAULT_PIXELS_PER_TICK, p * 1.25));
  }, []);
  const zoomHOut = useCallback(() => {
    setPixelsPerTick((p) => Math.max(MIN_HORIZONTAL_ZOOM * DEFAULT_PIXELS_PER_TICK, p / 1.25));
  }, []);
  const zoomVIn = useCallback(() => {
    setRowHeight((r) => Math.min(MAX_ROW_HEIGHT, r + 2));
  }, []);
  const zoomVOut = useCallback(() => {
    setRowHeight((r) => Math.max(MIN_ROW_HEIGHT, r - 2));
  }, []);
  const resetZoom = useCallback(() => {
    setPixelsPerTick(DEFAULT_PIXELS_PER_TICK);
    setRowHeight(DEFAULT_ROW_HEIGHT);
  }, []);

  const fitTrack = useCallback(
    (
      notes: Array<{ pitch: number; startTick: number; durationTick: number }>,
      ppq: number,
      meter: { numerator: number; denominator: number },
      containerWidth: number,
      containerHeight: number,
    ) => {
      // empty track → 用 fallback 时间范围 + 通用 pitch range
      if (!notes.length) {
        const fw = Math.max(containerWidth, 480);
        const fh = Math.max(containerHeight, 200);
        setPixelsPerTick(Math.max(DEFAULT_PIXELS_PER_TICK / 2, fw / Math.max(1, ticksPerBar(ppq, meter) * 4)));
        setRowHeight(Math.max(MIN_ROW_HEIGHT, Math.min(MAX_ROW_HEIGHT, fh / 24)));
        setScrollLeft(0);
        setScrollTop(0);
        return;
      }
      const minP = Math.min(...notes.map((n) => n.pitch));
      const maxP = Math.max(...notes.map((n) => n.pitch));
      const firstTick = Math.min(...notes.map((n) => n.startTick));
      const lastTick = Math.max(...notes.map((n) => n.startTick + n.durationTick));
      const span = Math.max(1, lastTick - firstTick);
      const pad = Math.max(480, span * 0.15);
      const totalTicks = span + pad * 2;
      const usableW = Math.max(containerWidth, 320);
      const usableH = Math.max(containerHeight, 160);

      // 受 min/max 约束的 zoom（避免单 note 占满屏幕）
      const fittedH = Math.max(0.4, Math.min(MAX_HORIZONTAL_ZOOM, usableW / Math.max(1, totalTicks)));
      setPixelsPerTick(fittedH * DEFAULT_PIXELS_PER_TICK);
      const pitchSpan = Math.max(12, maxP - minP + 6);
      const fittedRow = Math.max(MIN_ROW_HEIGHT, Math.min(MAX_ROW_HEIGHT, usableH / pitchSpan));
      setRowHeight(fittedRow);
      setScrollLeft(Math.max(0, firstTick * (fittedH * DEFAULT_PIXELS_PER_TICK) - pad));
      setScrollTop(Math.max(0, (maxP - maxP) * fittedRow)); // top aligns to max pitch
    },
    [],
  );

  // songId/document change → reset viewport transient state（由外部调用 resetZoom / fitTrack）
  useEffect(() => {
    setScrollLeft(0);
    setScrollTop(0);
  }, []);

  return {
    pixelsPerTick,
    rowHeight,
    scrollLeft,
    scrollTop,
    setScrollLeft,
    setScrollTop,
    zoomHIn,
    zoomHOut,
    zoomVIn,
    zoomVOut,
    resetZoom,
    horizontalPercent,
    fitTrack,
  };
}
