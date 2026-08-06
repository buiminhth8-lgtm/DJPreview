import { useState } from "react";
import type {
  AssetsResponse,
  DiffItem,
  GenerateFromReferenceResponse,
  OptimizeResponse,
  RegenerationResult,
} from "./api/types";
import { WorkspaceDashboard } from "./components/workspace";
import { useAudioAssets, useSongProject, useStyles, useVersions } from "./hooks";

export default function App() {
  const songProject = useSongProject();
  const styles = useStyles();
  const [styleStrength, setStyleStrength] = useState(0.7);
  const [pianoRefreshKey, setPianoRefreshKey] = useState(0);
  const [lastDiff, setLastDiff] = useState<DiffItem[] | null>(null);

  const audioAssets = useAudioAssets(songProject.songId);
  const versions = useVersions({ songId: songProject.songId });

  const loadProject = async (newSongId: string) => {
    const spec = await songProject.loadSong(newSongId);
    if (!spec) return;
    audioAssets.resetAssets();
    versions.resetVersions();
    setLastDiff(null);
    setPianoRefreshKey((k) => k + 1);
  };

  const handleGenerate = async () => {
    audioAssets.resetAssets();
    versions.resetVersions();
    setLastDiff(null);
    await songProject.generate(songProject.prompt, styles.selectedStyleId, styleStrength);
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
