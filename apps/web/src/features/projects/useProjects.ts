// features/projects/useProjects.ts（T33.2）
// 工程列表 hook：项目 → projectApi.listProjects。
// 不做搜索/分页/筛选（T33.3），只提供基础加载与删除。

import { useCallback, useEffect, useRef, useState } from "react";

import { deleteProject as deleteProjectApi, listProjects } from "./projectApi";
import type { ProjectSummary } from "./projectTypes";

export interface UseProjectsResult {
  projects: ProjectSummary[];
  isLoading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  removeProject: (songId: string) => Promise<boolean>;
}

export function useProjects(): UseProjectsResult {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reload = useCallback(async (): Promise<void> => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setIsLoading(true);
    setError(null);
    try {
      const list = await listProjects({ signal: controller.signal });
      setProjects(list);
    } catch (e) {
      if ((e as { code?: string }).code === "ABORTED") return;
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (!controller.signal.aborted) setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
    return () => abortRef.current?.abort();
  }, [reload]);

  const removeProject = useCallback(async (songId: string): Promise<boolean> => {
    try {
      await deleteProjectApi(songId);
      setProjects((prev) => prev.filter((p) => p.songId !== songId));
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      return false;
    }
  }, []);

  return { projects, isLoading, error, reload, removeProject };
}
