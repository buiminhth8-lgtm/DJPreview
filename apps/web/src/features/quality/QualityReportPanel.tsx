import { useState } from "react";
import {
  checkQuality,
  getQualityReport,
  optimizeArrangement,
  type OptimizeResponse,
  type QualityReport as QualityReportData,
} from "../../api/musicApi";

interface QualityReportProps {
  songId: string;
  onOptimized: (result: OptimizeResponse) => void;
  onError: (message: string) => void;
}

export default function QualityReportPanel({ songId, onOptimized, onError }: QualityReportProps) {
  const [report, setReport] = useState<QualityReportData | null>(null);
  const [busy, setBusy] = useState(false);

  const handleCheck = async () => {
    setBusy(true);
    try {
      const result = await checkQuality(songId);
      setReport(result);
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const handleLoad = async () => {
    setBusy(true);
    try {
      const result = await getQualityReport(songId);
      setReport(result);
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const handleOptimize = async () => {
    setBusy(true);
    try {
      const result = await optimizeArrangement(songId, true);
      setReport(result.quality_report_before);
      onOptimized(result);
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="quality-panel">
      <div className="actions">
        <button onClick={handleCheck} disabled={busy}>
          {busy ? "处理中…" : "检查质量"}
        </button>
        <button onClick={handleLoad} disabled={busy}>
          读取报告
        </button>
        <button onClick={handleOptimize} disabled={busy}>
          自动优化
        </button>
      </div>
      {report && (
        <div className="quality-report">
          <div className="summary">
            <div className="summary-row">
              <span className="summary-label">评分</span>
              <span className="summary-value">{Math.round(report.score)}/100（{report.level}）</span>
            </div>
            <div className="summary-row">
              <span className="summary-label">摘要</span>
              <span className="summary-value">{report.summary}</span>
            </div>
          </div>
          {report.issues.length > 0 && (
            <ul className="quality-issues">
              {report.issues.map((issue, i) => (
                <li key={i} className={`issue-${issue.severity}`}>
                  [{issue.severity}] {issue.category}: {issue.message}
                  {issue.suggestion ? `（建议：${issue.suggestion}）` : ""}
                </li>
              ))}
            </ul>
          )}
          {report.suggestions.length > 0 && (
            <div className="quality-suggestions">
              <strong>建议：</strong>
              {report.suggestions.join("；")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
