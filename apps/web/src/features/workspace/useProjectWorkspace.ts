// features/workspace/useProjectWorkspace.ts（T33.5）
// 工程工作台协调层：songId（URL）→ 页面级 project 状态（useProject）+ 业务 hooks 组合。
//
// 职责边界：
// - 页面级：loading / 404 / error / reload（来自 useProject）
// - 工作台：把 useProject 取得的 musicSpec 注入 useSongProject，避免重复请求 getSong
// - 协调：切换 songId 时清理旧工程资产（MIDI/WAV/versions），防旧请求覆盖
// 不包含 MIDI/audio/versions/tasks 的具体业务状态（各自 hook 负责）。

import { useEffect, useRef, useState } from "react";

import type { MusicSpec } from "../../api/types";
import { useProject } from "../projects/useProject";
import { useAudioAssets, useSongProject, useStyles, useVersions } from "../../hooks";

export interface UseProjectWorkspaceResult {
  songId: string | null;
  projectIsLoading: boolean;
  projectError: string | null;
  projectNotFound: boolean;
  reloadProject: () => Promise<void>;
  songProject: ReturnType<typeof useSongProject>;
  audioAssets: ReturnType<typeof useAudioAssets>;
  versions: ReturnType<typeof useVersions>;
  styles: ReturnType<typeof useStyles>;
  styleStrength: number;
  setStyleStrength: (value: number) => void;
  pianoRefreshKey: number;
  refreshPiano: () => void;
}

export function useProjectWorkspace(songId: string | undefined | null): UseProjectWorkspaceResult {
  const projectQuery = useProject(songId);
  const songProject = useSongProject();
  const styles = useStyles();
  const [styleStrength, setStyleStrength] = useState(0.7);
  const [pianoRefreshKey, setPianoRefreshKey] = useState(0);

  const audioAssets = useAudioAssets(songProject.songId);
  const versions = useVersions({ songId: songProject.songId });

  // 最新实例引用：effect 闭包始终调用当前 songId 绑定的 hook
  const audioAssetsRef = useRef(audioAssets);
  audioAssetsRef.current = audioAssets;
  const versionsRef = useRef(versions);
  versionsRef.current = versions;
  const songProjectRef = useRef(songProject);
  songProjectRef.current = songProject;

  // songId 变化 → 立即清理旧工程资产（不等详情返回）
  useEffect(() => {
    if (!songId) return;
    const current = songProjectRef.current;
    if (current.songId === songId) return; // 同一工程：由详情 effect 刷新
    audioAssetsRef.current.resetAssets();
    versionsRef.current.resetVersions();
    setPianoRefreshKey((k) => k + 1);
  }, [songId]);

  // project 详情就绪 → 注入 useSongProject（避免重复 getSong）+ 刷新资产/版本
  useEffect(() => {
    if (!songId) return;
    const current = songProjectRef.current;
    if (current.songId === songId) {
      void audioAssetsRef.current.refreshAssets();
      void versionsRef.current.refreshVersions();
      return;
    }
    const detail = projectQuery.project;
    if (detail && typeof detail.musicSpec === "object" && detail.musicSpec !== null) {
      current.setSongId(songId);
      current.setMusicSpec(detail.musicSpec as MusicSpec);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [songId, projectQuery.project, songProject.songId]);

  return {
    songId: songId ?? null,
    projectIsLoading: projectQuery.isLoading,
    projectError: projectQuery.error,
    projectNotFound: projectQuery.notFound,
    reloadProject: projectQuery.reload,
    songProject,
    audioAssets,
    versions,
    styles,
    styleStrength,
    setStyleStrength,
    pianoRefreshKey,
    refreshPiano: () => setPianoRefreshKey((k) => k + 1),
  };
}
