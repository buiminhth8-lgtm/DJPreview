// features/generation/useGenerateSong.ts（T33.4）
// 生成状态只属于 CreatePage：prompt/style 输入 + generate + result。
// 防重复提交、unmount 取消旧请求；不写入全局 Workspace 状态。

import { useCallback, useEffect, useRef, useState } from "react";

import { generateSong } from "./generationApi";
import type { GeneratedProjectSummary } from "./generationTypes";
import { getErrorMessage } from "../../hooks/error";

export interface UseGenerateSongResult {
  prompt: string;
  setPrompt: (value: string) => void;
  styleTemplateId: string;
  setStyleTemplateId: (value: string) => void;
  styleStrength: number;
  setStyleStrength: (value: number) => void;
  generate: () => Promise<GeneratedProjectSummary | null>;
  isGenerating: boolean;
  error: string | null;
  result: GeneratedProjectSummary | null;
  reset: () => void;
}

export function useGenerateSong(): UseGenerateSongResult {
  const [prompt, setPrompt] = useState("");
  const [styleTemplateId, setStyleTemplateId] = useState("");
  const [styleStrength, setStyleStrength] = useState(0.7);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GeneratedProjectSummary | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const inFlightRef = useRef(false);

  const generate = useCallback(async (): Promise<GeneratedProjectSummary | null> => {
    if (inFlightRef.current) return null;
    const trimmed = prompt.trim();
    if (!trimmed) {
      setError("请输入音乐描述");
      return null;
    }
    inFlightRef.current = true;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setIsGenerating(true);
    setError(null);
    try {
      const summary = await generateSong(
        {
          prompt: trimmed,
          styleTemplateId: styleTemplateId || null,
          styleStrength,
        },
        { signal: controller.signal },
      );
      if (controller.signal.aborted) return null;
      setResult(summary);
      return summary;
    } catch (e) {
      if ((e as { code?: string }).code === "ABORTED") return null;
      setError(getErrorMessage(e));
      return null;
    } finally {
      inFlightRef.current = false;
      if (!controller.signal.aborted) setIsGenerating(false);
    }
  }, [prompt, styleTemplateId, styleStrength]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setResult(null);
    setError(null);
    setIsGenerating(false);
    inFlightRef.current = false;
  }, []);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  return {
    prompt,
    setPrompt,
    styleTemplateId,
    setStyleTemplateId,
    styleStrength,
    setStyleStrength,
    generate,
    isGenerating,
    error,
    result,
    reset,
  };
}
