// useEvaluation：评估用例与批量评估。

import { useCallback, useState } from "react";

import { listEvalCases, runEvaluation as runEvaluationApi } from "../api/evaluationApi";
import type { EvalCase, EvalReport } from "../api/types";
import { getErrorMessage } from "./error";

export function useEvaluation() {
  const [evaluationCases, setEvaluationCases] = useState<EvalCase[] | null>(null);
  const [evaluationReport, setEvaluationReport] = useState<EvalReport | null>(null);
  const [loadingCases, setLoadingCases] = useState(false);
  const [runningEvaluation, setRunningEvaluation] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadEvaluationCases = useCallback(async (): Promise<EvalCase[] | null> => {
    setLoadingCases(true);
    setError(null);
    try {
      const cases = await listEvalCases();
      setEvaluationCases(cases);
      return cases;
    } catch (e) {
      setError(getErrorMessage(e));
      return null;
    } finally {
      setLoadingCases(false);
    }
  }, []);

  const runEvaluation = useCallback(
    async (caseIds: string[], renderAudio = false): Promise<EvalReport | null> => {
      setRunningEvaluation(true);
      setError(null);
      try {
        const report = await runEvaluationApi(caseIds, renderAudio);
        setEvaluationReport(report);
        return report;
      } catch (e) {
        setError(getErrorMessage(e));
        return null;
      } finally {
        setRunningEvaluation(false);
      }
    },
    [],
  );

  return {
    evaluationCases,
    evaluationReport,
    loadingCases,
    runningEvaluation,
    error,
    setError,
    loadEvaluationCases,
    runEvaluation,
  };
}
