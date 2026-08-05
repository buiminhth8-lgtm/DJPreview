// useQuality：质量检查 / 报告 / 自动优化。

import { useCallback, useState } from "react";

import { checkQuality, getQualityReport, optimizeArrangement } from "../api/analysisApi";
import type { OptimizeResponse, QualityReport } from "../api/types";
import { getErrorMessage } from "./error";

export function useQuality(songId?: string | null) {
  const [qualityReport, setQualityReport] = useState<QualityReport | null>(null);
  const [loadingQuality, setLoadingQuality] = useState(false);
  const [optimizingQuality, setOptimizingQuality] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runQualityCheck = useCallback(async (): Promise<QualityReport | null> => {
    if (!songId) return null;
    setLoadingQuality(true);
    setError(null);
    try {
      const report = await checkQuality(songId);
      setQualityReport(report);
      return report;
    } catch (e) {
      setError(getErrorMessage(e));
      return null;
    } finally {
      setLoadingQuality(false);
    }
  }, [songId]);

  const refreshQualityReport = useCallback(async (): Promise<QualityReport | null> => {
    if (!songId) return null;
    setLoadingQuality(true);
    setError(null);
    try {
      const report = await getQualityReport(songId);
      setQualityReport(report);
      return report;
    } catch (e) {
      setError(getErrorMessage(e));
      return null;
    } finally {
      setLoadingQuality(false);
    }
  }, [songId]);

  const optimizeQuality = useCallback(
    async (autoRender = true): Promise<OptimizeResponse | null> => {
      if (!songId) return null;
      setOptimizingQuality(true);
      setError(null);
      try {
        const result = await optimizeArrangement(songId, autoRender);
        setQualityReport(result.quality_report_before);
        return result;
      } catch (e) {
        setError(getErrorMessage(e));
        return null;
      } finally {
        setOptimizingQuality(false);
      }
    },
    [songId],
  );

  return {
    qualityReport,
    loadingQuality,
    optimizingQuality,
    error,
    setError,
    runQualityCheck,
    refreshQualityReport,
    optimizeQuality,
  };
}
