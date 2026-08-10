// features/midi/editor/TimelineHeader.tsx（T34.3）
// 顶部时间轴：bar 编号，基于 PPQ + time signature。

import type { MeterInfo } from "./midiEditorLayout";
import { ticksPerBar, visibleBarCount } from "./midiEditorLayout";

export interface TimelineHeaderProps {
  ppq: number;
  meter: MeterInfo;
  maxTick: number;
  pixelsPerTick: number;
}

export function TimelineHeader({ ppq, meter, maxTick, pixelsPerTick }: TimelineHeaderProps) {
  const perBar = ticksPerBar(ppq, meter);
  const bars = visibleBarCount(maxTick, ppq, meter);
  const width = Math.max(1, bars * perBar * pixelsPerTick);

  return (
    <div className="midi-editor__timeline" style={{ width }}>
      {Array.from({ length: bars }, (_, i) => (
        <div
          key={i}
          className="midi-editor__bar"
          style={{ left: i * perBar * pixelsPerTick }}
        >
          <span className="midi-editor__bar-label">{i + 1}</span>
        </div>
      ))}
    </div>
  );
}
