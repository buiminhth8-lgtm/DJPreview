// features/midi/editor/TimelineHeader.tsx（T34.3）
// 顶部时间轴：bar 编号，基于 PPQ + time signature。

import type { MeterInfo } from "./midiEditorLayout";
import { ticksPerBar, visibleBarCount } from "./midiEditorLayout";

export interface TimelineHeaderProps {
  ppq: number;
  meter: MeterInfo;
  maxTick: number;
  pixelsPerTick: number;
  currentTick?: number;
  loopEnabled?: boolean;
  loopStartTick?: number;
  loopEndTick?: number;
  onSeek?: (tick: number) => void;
}

export function TimelineHeader({
  ppq,
  meter,
  maxTick,
  pixelsPerTick,
  currentTick = 0,
  loopEnabled = false,
  loopStartTick = 0,
  loopEndTick = 0,
  onSeek,
}: TimelineHeaderProps) {
  const perBar = ticksPerBar(ppq, meter);
  const bars = visibleBarCount(Math.max(maxTick, currentTick, loopEndTick), ppq, meter);
  const width = Math.max(1, bars * perBar * pixelsPerTick);

  const handleSeek = (event: React.MouseEvent<HTMLDivElement>) => {
    if (!onSeek) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = Math.max(0, Math.min(width, event.clientX - rect.left));
    onSeek(Math.round(x / pixelsPerTick));
  };

  return (
    <div
      className="midi-editor__timeline"
      style={{ width }}
      onClick={handleSeek}
      role="slider"
      aria-label="MIDI 时间轴，点击定位"
      aria-valuemin={0}
      aria-valuemax={bars * perBar}
      aria-valuenow={Math.round(currentTick)}
      tabIndex={0}
    >
      {loopEnabled && loopEndTick > loopStartTick && (
        <div
          className="midi-editor__loop-region"
          data-testid="timeline-loop-region"
          style={{
            left: loopStartTick * pixelsPerTick,
            width: (loopEndTick - loopStartTick) * pixelsPerTick,
          }}
        />
      )}
      {Array.from({ length: bars }, (_, i) => (
        <div
          key={i}
          className="midi-editor__bar"
          style={{ left: i * perBar * pixelsPerTick }}
        >
          <span className="midi-editor__bar-label">{i + 1}</span>
        </div>
      ))}
      <div
        className="midi-editor__timeline-playhead"
        data-testid="timeline-playhead"
        style={{ left: currentTick * pixelsPerTick }}
      />
    </div>
  );
}
