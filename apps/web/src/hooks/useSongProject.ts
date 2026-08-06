// useSongProject：歌曲 / 项目核心状态（生成、读取、编辑、重置）+ 生成调试日志（T35）。

import { useCallback, useState } from "react";

import { ApiRequestError } from "../api/client";
import { editSong, generateMusicSpec, getSong } from "../api/songApi";
import type {
  EditSongResponse,
  GenerateSongResponse,
  GenerationDebug,
  MusicSpec,
  WarningItem,
} from "../api/types";
import { getErrorMessage } from "./error";

export type GenerationStatus = "idle" | "sending" | "success" | "failed";

export interface GenerationLogEntry {
  level: "info" | "warning" | "error";
  message: string;
  requestId?: string;
  code?: string;
  stage?: string;
}

export interface GenerationErrorInfo {
  message: string;
  code?: string;
  stage?: string;
  status?: number;
  requestId?: string;
  provider?: string;
  rawBodyPreview?: string;
  finish_reason?: string;
  content_chars?: number;
  raw_response_path?: string;
  message_content_path?: string;
  hint?: string;
}

export function useSongProject() {
  const [songId, setSongId] = useState<string | null>(null);
  const [musicSpec, setMusicSpec] = useState<MusicSpec | null>(null);
  const [prompt, setPrompt] = useState("");
  const [editInstruction, setEditInstruction] = useState("");
  const [validation, setValidation] = useState<GenerateSongResponse["validation"]>(null);
  const [loadingSpec, setLoadingSpec] = useState(false);
  const [loadingEdit, setLoadingEdit] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // T35：生成调试状态
  const [generationStatus, setGenerationStatus] = useState<GenerationStatus>("idle");
  const [generationLog, setGenerationLog] = useState<GenerationLogEntry[]>([]);
  const [generationRequestId, setGenerationRequestId] = useState<string | null>(null);
  const [generationDebug, setGenerationDebug] = useState<GenerationDebug | null>(null);
  const [generationWarnings, setGenerationWarnings] = useState<WarningItem[]>([]);
  const [generationErrorInfo, setGenerationErrorInfo] = useState<GenerationErrorInfo | null>(null);

  const appendLog = useCallback((entry: GenerationLogEntry) => {
    setGenerationLog((prev) => [...prev, entry]);
  }, []);

  const resetGenerationDebug = useCallback(() => {
    setGenerationStatus("sending");
    setGenerationLog([{ level: "info", message: "Sending generate MusicSpec request" }]);
    setGenerationRequestId(null);
    setGenerationDebug(null);
    setGenerationWarnings([]);
    setGenerationErrorInfo(null);
  }, []);

  const resetProject = useCallback(() => {
    setSongId(null);
    setMusicSpec(null);
    setValidation(null);
    setPrompt("");
    setEditInstruction("");
    setError(null);
    setGenerationStatus("idle");
    setGenerationLog([]);
    setGenerationRequestId(null);
    setGenerationDebug(null);
    setGenerationWarnings([]);
    setGenerationErrorInfo(null);
  }, []);

  const generate = useCallback(
    async (
      promptText: string,
      styleTemplateId?: string | null,
      styleStrength = 0.7,
    ): Promise<GenerateSongResponse | null> => {
      if (!promptText.trim()) {
        setError("请输入音乐描述");
        return null;
      }
      setLoadingSpec(true);
      setError(null);
      resetGenerationDebug();
      try {
        const result = await generateMusicSpec(promptText.trim(), styleTemplateId || null, styleStrength);
        setSongId(result.song_id);
        setMusicSpec(result.music_spec);
        setValidation(result.validation ?? null);
        setGenerationStatus("success");
        setGenerationRequestId(result.request_id ?? null);
        setGenerationDebug(result.debug ?? null);
        setGenerationWarnings(result.warnings ?? []);
        appendLog({ level: "info", message: "API response received", requestId: result.request_id ?? undefined });
        for (const w of result.warnings ?? []) {
          appendLog({ level: "warning", message: `MusicSpec validation warning: ${w.message}`, code: w.code });
        }
        return result;
      } catch (e) {
        const info = toGenerationErrorInfo(e);
        setGenerationStatus("failed");
        setGenerationErrorInfo(info);
        setGenerationRequestId(info.requestId ?? null);
        appendLog({
          level: "error",
          message: info.message,
          code: info.code,
          stage: info.stage,
          requestId: info.requestId,
        });
        setError(getErrorMessage(e));
        return null;
      } finally {
        setLoadingSpec(false);
      }
    },
    [appendLog, resetGenerationDebug],
  );

  const loadSong = useCallback(async (newSongId: string): Promise<MusicSpec | null> => {
    try {
      const result = await getSong(newSongId);
      setSongId(newSongId);
      setMusicSpec(result.music_spec);
      return result.music_spec;
    } catch (e) {
      setError(getErrorMessage(e));
      return null;
    }
  }, []);

  const edit = useCallback(
    async (instruction: string, autoRender = true): Promise<EditSongResponse | null> => {
      if (!songId) {
        setError("请先生成或加载歌曲");
        return null;
      }
      if (!instruction.trim()) {
        setError("请输入修改指令");
        return null;
      }
      setLoadingEdit(true);
      setError(null);
      try {
        const result = await editSong(songId, instruction.trim(), autoRender);
        setMusicSpec(result.music_spec);
        return result;
      } catch (e) {
        setError(getErrorMessage(e));
        return null;
      } finally {
        setLoadingEdit(false);
      }
    },
    [songId],
  );

  return {
    songId,
    setSongId,
    musicSpec,
    setMusicSpec,
    prompt,
    setPrompt,
    editInstruction,
    setEditInstruction,
    validation,
    loadingSpec,
    loadingEdit,
    error,
    setError,
    generate,
    loadSong,
    edit,
    resetProject,
    // T35
    generationStatus,
    generationLog,
    generationRequestId,
    generationDebug,
    generationWarnings,
    generationErrorInfo,
  };
}

export function toGenerationErrorInfo(e: unknown): GenerationErrorInfo {
  if (e instanceof ApiRequestError) {
    const d = (e.details ?? {}) as Record<string, unknown>;
    return {
      message: e.message,
      code: e.code,
      stage: e.stage,
      status: e.status,
      requestId: e.requestId,
      provider: e.provider ?? (typeof d.provider === "string" ? d.provider : undefined),
      rawBodyPreview: e.rawBodyPreview,
      finish_reason: typeof d.finish_reason === "string" ? d.finish_reason : undefined,
      content_chars: typeof d.content_chars === "number" ? d.content_chars : undefined,
      raw_response_path: typeof d.raw_response_path === "string" ? d.raw_response_path : undefined,
      message_content_path: typeof d.message_content_path === "string" ? d.message_content_path : undefined,
      hint: typeof d.hint === "string" ? d.hint : undefined,
    };
  }
  return { message: getErrorMessage(e) };
}
