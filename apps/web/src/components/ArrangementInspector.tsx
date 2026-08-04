import type { MusicSpec, OptimizeResponse } from "../api/musicApi";
import MusicSummary from "./MusicSummary";
import PianoRoll from "./PianoRoll";
import QualityReportPanel from "./QualityReport";
import SectionTimeline from "./SectionTimeline";
import TrackList from "./TrackList";

interface ArrangementInspectorProps {
  songId: string;
  spec: MusicSpec;
  refreshKey: number;
  onOptimized: (result: OptimizeResponse) => void;
  onError: (message: string) => void;
}

export default function ArrangementInspector({
  songId,
  spec,
  refreshKey,
  onOptimized,
  onError,
}: ArrangementInspectorProps) {
  return (
    <div className="arrangement-inspector">
      <h3>MusicSpec 摘要</h3>
      <MusicSummary spec={spec} />
      <h3>段落结构</h3>
      <SectionTimeline sections={spec.form} />
      <h3>轨道列表</h3>
      <TrackList tracks={spec.tracks} />
      <h3>钢琴卷帘</h3>
      <PianoRoll songId={songId} refreshKey={refreshKey} onError={onError} />
      <h3>编曲质量</h3>
      <QualityReportPanel songId={songId} onOptimized={onOptimized} onError={onError} />
    </div>
  );
}
