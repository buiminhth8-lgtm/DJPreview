// features/midi/editor/useMidiEditorDocument.ts（T34.1）
// 只读 hook：加载 MidiEditorDocument。
// songId 缺失不发请求；变化重载；AbortController 防竞态；unmount 取消。

import { useCallback, useEffect, useRef, useState } from "react";

import { getMidiEditorDocument } from "./midiEditorApi";
import type { MidiEditorDocument } from "./midiEditorTypes";
import { getErrorMessage } from "../../../hooks/error";

export interface UseMidiEditorDocumentResult {
  document: MidiEditorDocument | null;
  isLoading: boolean;
  error: string | null;
  notFound: boolean;
  reload: () => Promise<void>;
}

export function useMidiEditorDocument(songId: string | undefined | null): UseMidiEditorDocumentResult {
  const [document, setDocument] = useState<MidiEditorDocument | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const reload = useCallback(async (): Promise<void> => {
    abortRef.current?.abort();
    if (!songId || !songId.trim()) {
      setDocument(null);
      setError(null);
      setNotFound(false);
      return;
    }
    const controller = new AbortController();
    abortRef.current = controller;
    // Never keep project A's document visible while project B is loading.
    setDocument((current) => current?.songId === songId ? current : null);
    setIsLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const doc = await getMidiEditorDocument(songId, { signal: controller.signal });
      if (controller.signal.aborted) return;
      setDocument(doc);
    } catch (e) {
      if ((e as { code?: string }).code === "ABORTED") return;
      const err = e as { status?: number; code?: string };
      if (err.status === 404) {
        setNotFound(true);
      }
      setError(getErrorMessage(e));
    } finally {
      if (!controller.signal.aborted) setIsLoading(false);
    }
  }, [songId]);

  useEffect(() => {
    void reload();
    return () => abortRef.current?.abort();
  }, [reload]);

  return { document, isLoading, error, notFound, reload };
}
