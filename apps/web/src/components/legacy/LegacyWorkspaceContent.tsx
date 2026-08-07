// LegacyWorkspaceContent：T33.1 过渡组件。
// 把 App.tsx 原有的工作台状态与回调原样保留，接收 songId（来自 URL），
// 并在 songId 变化时加载工程，支持直接打开/刷新 /projects/:songId。
// 后续 T33.5/T33.6 再拆分为正式 feature。

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import type {
  AssetsResponse,
  DiffItem,
  GenerateFromReferenceResponse,
  OptimizeResponse,
  RegenerationResult,
} from "../../api/types";
import { WorkspaceDashboard } from "../../components/workspace";
import { useAudioAssets, useSongProject, useStyles, useVersions } from "../../hooks";

export interface LegacyWorkspaceContentProps {
  songId?: string | null;
}

export default function LegacyWorkspaceContent({ songId = null }: LegacyWorkspaceContentProps) {
  const navigate = useNavigate();
  const songProject = useSongProject();
  const styles = useStyles();
  const [styleStrength, setStyleStrength] = useState(0.7);
  const [pianoRefreshKey, setPianoRefreshKey] = useState(0);
  const [lastDiff, setLastDiff] = useState<DiffItem[] | null>(null);

  const audioAssets = useAudioAssets(songProject.songId);
  const versions = useVersions({ songId: songProject.songId });

  // songId 来自 URL：首次进入或刷新时加载工程
  useEffect(() => {
    if (!songId) return;
    if (songProject.songId === songId) {
      // 已加载同一工程：刷新资产与版本
      void audioAssets.refreshAssets();
      void versions.refreshVersions();
      return;
    }
    let cancelled = false;
    void songProject.loadSong(songId).then((spec) => {
      if (cancelled || !spec) return;
      audioAssets.resetAssets();
      versions.resetVersions();
      setLastDiff(null);
      setPianoRefreshKey((k) => k + 1);
      void audioAssets.refreshAssets();
      void versions.refreshVersions();
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [songId]);

  const loadProject = async (newSongId: string) => {
    const spec = await songProject.loadSong(newSongId);
    if (!spec) return;
    audioAssets.resetAssets();
    versions.resetVersions();
    setLastDiff(null);
    setPianoRefreshKey((k) => k + 1);
    navigate(`/projects/${newSongId}`);
  };

  const handleGenerate = async () => {
    audioAssets.resetAssets();
    versions.resetVersions();
    setLastDiff(null);
    const result = await songProject.generate(songProject.prompt, styles.selectedStyleId, styleStrength);
    if (result?.song_id) {
      navigate(`/projects/${result.song_id}`);
    }
  };

  const handleGenerateMidi = async () => {
    await audioAssets.generateMidi();
  };

  const handleRenderAudio = async () => {
    await audioAssets.renderAudio();
  };

  const handleApplyEdit = async (autoRender = true) => {
    const result = await songProject.edit(songProject.editInstruction, autoRender);
    if (!result) return;
    setLastDiff(result.diff);
    audioAssets.updateFromAssets(result.assets);
    await versions.refreshVersions();
    setPianoRefreshKey((k) => k + 1);
  };

  const handleLoadVersions = async () => {
    await versions.refreshVersions();
  };

  const handleRestore = async (versionId: string) => {
    const result = await versions.restoreVersion(versionId);
    if (!result) return;
    songProject.setMusicSpec(result.music_spec);
    audioAssets.updateFromAssets(result.assets);
    await versions.refreshVersions();
    setPianoRefreshKey((k) => k + 1);
  };

  const handleMixApplied = (assets: AssetsResponse) => {
    audioAssets.updateFromAssets(assets);
    setPianoRefreshKey((k) => k + 1);
  };

  const handleOptimized = async (result: OptimizeResponse) => {
    songProject.setMusicSpec(result.music_spec);
    audioAssets.updateFromAssets(result.assets);
    await versions.refreshVersions();
    setPianoRefreshKey((k) => k + 1);
  };

  const handleRegenerated = async (result: RegenerationResult) => {
    songProject.setMusicSpec(result.music_spec);
    audioAssets.updateFromAssets(result.assets);
    await versions.refreshVersions();
    setPianoRefreshKey((k) => k + 1);
  };

  const handleGenerateFromReference = (result: GenerateFromReferenceResponse) => {
    void loadProject(result.song_id);
  };

  const handleImported = (newSongId: string) => {
    void loadProject(newSongId);
  };

  return (
    <WorkspaceDashboard
      songProject={songProject}
      audioAssets={audioAssets}
      versions={versions}
      styles={styles}
      styleStrength={styleStrength}
      setStyleStrength={setStyleStrength}
      pianoRefreshKey={pianoRefreshKey}
      lastDiff={lastDiff}
      onGenerate={() => void handleGenerate()}
      onGenerateMidi={() => void handleGenerateMidi()}
      onRenderAudio={() => void handleRenderAudio()}
      onApplyEdit={(autoRender) => void handleApplyEdit(autoRender)}
      onLoadVersions={() => void handleLoadVersions()}
      onRestore={(versionId) => void handleRestore(versionId)}
      onMixApplied={handleMixApplied}
      onOptimized={(result) => void handleOptimized(result)}
      onRegenerated={(result) => void handleRegenerated(result)}
      onGenerateFromReference={handleGenerateFromReference}
      onImported={handleImported}
    />
  );
}
