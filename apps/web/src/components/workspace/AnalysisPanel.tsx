// 编曲分析面板（摘要 / 段落 / 轨道 / 钢琴卷帘 / 质量）。

import type { MusicSpec, OptimizeResponse } from "../../api/types";
import ArrangementInspector from "../ArrangementInspector";

export interface AnalysisPanelProps {
  songId: string;
  spec: MusicSpec;
  refreshKey: number;
  onOptimized: (result: OptimizeResponse) => void;
  onError: (message: string) => void;
}

export default function AnalysisPanel({
  songId,
  spec,
  refreshKey,
  onOptimized,
  onError,
}: AnalysisPanelProps) {
  return (
    <section className="panel result">
      <h2>编曲检查（摘要 / 段落 / 轨道 / 钢琴卷帘 / 质量）</h2>
      <ArrangementInspector
        songId={songId}
        spec={spec}
        refreshKey={refreshKey}
        onOptimized={onOptimized}
        onError={onError}
      />
    </section>
  );
}
