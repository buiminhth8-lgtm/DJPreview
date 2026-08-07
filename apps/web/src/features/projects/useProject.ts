// features/projects/useProject.ts（T33.2）
// 单工程详情 hook：/projects/:songId 刷新恢复核心。
// songId 缺失不发请求；songId 变化重新加载；AbortController 防旧请求覆盖。

import { useCallback, useEffect, useRef, useState } from "react";

import { getProject } from "./projectApi";
import type { ProjectDetail } from "./projectTypes";

export interface UseProjectResult {
  project: ProjectDetail | null;
  isLoading: boolean;
  error: string | null;
  notFound: boolean;
  reload: () => Promise<void>;
}

export function useProject(songId: string | undefined | null): UseProjectResult {
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const reload = useCallback(async (): Promise<void> => {
    abortRef.current?.abort();
    if (!songId || !songId.trim()) {
      setProject(null);
      setError(null);
      setNotFound(false);
      return;
    }
    const controller = new AbortController();
    abortRef.current = controller;
    setIsLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const detail = await getProject(songId, { signal: controller.signal });
      if (controller.signal.aborted) return;
      setProject(detail);
    } catch (e) {
      if ((e as { code?: string }).code === "ABORTED") return;
      const err = e as { status?: number };
      if (err.status === 404) {
        setNotFound(true);
      }
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (!controller.signal.aborted) setIsLoading(false);
    }
  }, [songId]);

  useEffect(() => {
    void reload();
    return () => abortRef.current?.abort();
  }, [reload]);

  return { project, isLoading, error, notFound, reload };
}
