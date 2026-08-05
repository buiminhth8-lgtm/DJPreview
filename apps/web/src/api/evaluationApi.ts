// Evaluation 领域 API：用例列表、批量评估。

import { requestJson } from "./client";
import type { EvalCase, EvalReport } from "./types";

export interface EvaluationRunRequest {
  case_ids?: string[];
  render_audio?: boolean;
}

export function listEvalCases(): Promise<EvalCase[]> {
  return requestJson("/api/v1/evaluation/cases", "GET");
}

export function runEvaluation(caseIds: string[], renderAudio = false): Promise<EvalReport> {
  return requestJson("/api/v1/evaluation/run", "POST", { case_ids: caseIds, render_audio: renderAudio });
}
