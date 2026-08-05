// 批量评估面板（复用既有 EvaluationPanel）。

import EvaluationPanelInner from "../EvaluationPanel";

export interface EvaluationPanelProps {
  onError: (message: string) => void;
}

export default function EvaluationPanel({ onError }: EvaluationPanelProps) {
  return (
    <section className="panel result">
      <h2>批量评估</h2>
      <EvaluationPanelInner onError={onError} />
    </section>
  );
}
