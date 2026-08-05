// useReferenceMidi：参考 MIDI 分析 / 基于参考生成。

import { useCallback, useState } from "react";

import { analyzeReferenceMidi, generateFromReference } from "../api/referenceApi";
import type { GenerateFromReferenceResponse, ReferenceMidiAnalysis } from "../api/types";
import { getErrorMessage } from "./error";

export function useReferenceMidi() {
  const [referenceAnalysis, setReferenceAnalysis] = useState<ReferenceMidiAnalysis | null>(null);
  const [loadingReference, setLoadingReference] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyzeReference = useCallback(async (file: File): Promise<ReferenceMidiAnalysis | null> => {
    setLoadingReference(true);
    setError(null);
    try {
      const analysis = await analyzeReferenceMidi(file);
      setReferenceAnalysis(analysis);
      return analysis;
    } catch (e) {
      setError(getErrorMessage(e));
      return null;
    } finally {
      setLoadingReference(false);
    }
  }, []);

  const generateFromReferenceMidi = useCallback(
    async (
      file: File,
      prompt: string,
      styleTemplateId?: string | null,
      styleStrength = 0.7,
    ): Promise<GenerateFromReferenceResponse | null> => {
      setLoadingReference(true);
      setError(null);
      try {
        const result = await generateFromReference(file, prompt, styleTemplateId, styleStrength);
        return result;
      } catch (e) {
        setError(getErrorMessage(e));
        return null;
      } finally {
        setLoadingReference(false);
      }
    },
    [],
  );

  const clearReference = useCallback(() => {
    setReferenceAnalysis(null);
  }, []);

  return {
    referenceAnalysis,
    loadingReference,
    error,
    setError,
    analyzeReference,
    generateFromReference: generateFromReferenceMidi,
    clearReference,
  };
}
