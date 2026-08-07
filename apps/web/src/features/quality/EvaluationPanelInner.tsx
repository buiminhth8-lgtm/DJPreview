import { useEffect, useState } from "react";
import { listEvalCases, runEvaluation, type EvalCase, type EvalReport } from "../../api/musicApi";

interface EvaluationPanelProps {
  onError: (message: string) => void;
}

export default function EvaluationPanel({ onError }: EvaluationPanelProps) {
  const [cases, setCases] = useState<EvalCase[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [report, setReport] = useState<EvalReport | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listEvalCases()
      .then((list) => {
        setCases(list);
        setSelected(new Set(list.slice(0, 2).map((c) => c.id)));
      })
      .catch((e) => onError(e instanceof Error ? e.message : String(e)));
  }, [onError]);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleRun = async () => {
    if (selected.size === 0) {
      onError("请至少选择一个评估用例");
      return;
    }
    setBusy(true);
    try {
      const result = await runEvaluation([...selected], false);
      setReport(result);
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="evaluation-panel">
      <div className="eval-case-list">
        {cases.map((caseItem) => (
          <label key={caseItem.id} className="eval-case-item">
            <input
              type="checkbox"
              checked={selected.has(caseItem.id)}
              onChange={() => toggle(caseItem.id)}
            />
            {caseItem.id}（{caseItem.notes ?? caseItem.prompt.slice(0, 12)}）
          </label>
        ))}
      </div>
      <div className="actions">
        <button onClick={handleRun} disabled={busy}>
          {busy ? "评估中…" : "运行评估"}
        </button>
      </div>
      {report && (
        <div className="eval-report">
          <div className="summary">
            <div className="summary-row">
              <span className="summary-label">用例数</span>
              <span className="summary-value">{report.total_cases}</span>
            </div>
            <div className="summary-row">
              <span className="summary-label">通过</span>
              <span className="summary-value">{report.passed_cases}</span>
            </div>
            <div className="summary-row">
              <span className="summary-label">平均分</span>
              <span className="summary-value">{report.average_score}</span>
            </div>
            <div className="summary-row">
              <span className="summary-label">摘要</span>
              <span className="summary-value">{report.summary}</span>
            </div>
          </div>
          {report.results.map((result) => (
            <div className="eval-result" key={result.case_id}>
              <strong>
                {result.case_id}：{result.score} 分（质量 {result.quality_score}）
              </strong>
              {result.errors.length > 0 && <div className="error">错误：{result.errors.join("；")}</div>}
              {result.warnings.length > 0 && (
                <div className="warnings">警告：{result.warnings.join("；")}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
