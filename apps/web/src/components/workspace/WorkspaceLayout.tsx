// 工作台布局：组合各领域面板，不做业务逻辑。

import type { useAudioAssets, useSongProject, useStyles, useVersions } from "../../hooks";
import type {
  AssetsResponse,
  DiffItem,
  GenerateFromReferenceResponse,
  OptimizeResponse,
  RegenerationResult,
} from "../../api/types";
import RegenerationPanel from "../RegenerationPanel";
import AnalysisPanel from "./AnalysisPanel";
import EditPanel from "./EditPanel";
import EvaluationPanel from "./EvaluationPanel";
import GeneratePanel from "./GeneratePanel";
import MixerPanel from "./MixerPanel";
import PlayerPanel from "./PlayerPanel";
import ProjectPanel from "./ProjectPanel";
import ReferencePanel from "./ReferencePanel";
import VersionPanel from "./VersionPanel";
import WorkspaceHeader from "./WorkspaceHeader";

export interface WorkspaceLayoutProps {
  songProject: ReturnType<typeof useSongProject>;
  audioAssets: ReturnType<typeof useAudioAssets>;
  versions: ReturnType<typeof useVersions>;
  styles: ReturnType<typeof useStyles>;
  styleStrength: number;
  setStyleStrength: (value: number) => void;
  pianoRefreshKey: number;
  lastDiff: DiffItem[] | null;
  onGenerate: () => void;
  onGenerateMidi: () => void;
  onRenderAudio: () => void;
  onApplyEdit: () => void;
  onLoadVersions: () => void;
  onRestore: (versionId: string) => void;
  onMixApplied: (assets: AssetsResponse) => void;
  onOptimized: (result: OptimizeResponse) => void;
  onRegenerated: (result: RegenerationResult) => void;
  onGenerateFromReference: (result: GenerateFromReferenceResponse) => void;
  onImported: (songId: string) => void;
}

export default function WorkspaceLayout({
  songProject,
  audioAssets,
  versions,
  styles,
  styleStrength,
  setStyleStrength,
  pianoRefreshKey,
  lastDiff,
  onGenerate,
  onGenerateMidi,
  onRenderAudio,
  onApplyEdit,
  onLoadVersions,
  onRestore,
  onMixApplied,
  onOptimized,
  onRegenerated,
  onGenerateFromReference,
  onImported,
}: WorkspaceLayoutProps) {
  const songId = songProject.songId;
  const spec = songProject.musicSpec;
  const hasSong = Boolean(songId && spec);

  return (
    <div className="container workspace">
      <WorkspaceHeader
        songId={songProject.songId}
        currentVersionId={versions.currentVersionId}
        hasMidi={Boolean(audioAssets.assets?.has_midi)}
        hasAudio={Boolean(audioAssets.assets?.has_audio)}
        error={songProject.error}
      />

      <div className="workspace-grid">
        <div className="workspace-column">
          <GeneratePanel
            prompt={songProject.prompt}
            loading={songProject.loadingSpec}
            styleId={styles.selectedStyleId}
            styleStrength={styleStrength}
            validation={songProject.validation}
            onPromptChange={songProject.setPrompt}
            onStyleChange={(id, strength) => {
              styles.setSelectedStyleId(id);
              setStyleStrength(strength);
            }}
            onError={songProject.setError}
            onGenerate={onGenerate}
          />
          {hasSong && songId && spec && (
            <>
              <EditPanel
                value={songProject.editInstruction}
                loading={songProject.loadingEdit}
                diff={lastDiff}
                onChange={songProject.setEditInstruction}
                onApply={onApplyEdit}
              />
              <ProjectPanel
                songId={songId}
                onImported={onImported}
                onError={songProject.setError}
              />
            </>
          )}
        </div>

        <div className="workspace-column">
          {hasSong && songId && spec && (
            <>
              <PlayerPanel
                songId={songId}
                midiResult={audioAssets.midiResult}
                audioResult={audioAssets.audioResult}
                audioStreamUrl={audioAssets.audioStreamUrl}
                midiDownloadUrl={audioAssets.midiDownloadUrl}
                audioDownloadUrl={audioAssets.audioDownloadUrl}
                loadingMidi={audioAssets.loadingMidi}
                loadingAudio={audioAssets.loadingAudio}
                onGenerateMidi={onGenerateMidi}
                onRenderAudio={onRenderAudio}
                onError={songProject.setError}
              />
              <VersionPanel
                versions={versions.versions}
                currentVersionId={versions.currentVersionId}
                loading={versions.loadingVersions}
                onLoad={onLoadVersions}
                onRestore={onRestore}
              />
              <MixerPanel
                songId={songId}
                refreshKey={pianoRefreshKey}
                onApplied={onMixApplied}
                onError={songProject.setError}
              />
              <AnalysisPanel
                songId={songId}
                spec={spec}
                refreshKey={pianoRefreshKey}
                onOptimized={onOptimized}
                onError={songProject.setError}
              />
            </>
          )}
        </div>
      </div>

      {hasSong && songId && spec && (
        <>
          <div className="workspace-grid">
            <div className="workspace-column">
              <section className="panel result">
                <h2>局部重生成</h2>
                <RegenerationPanel
                  songId={songId}
                  spec={spec}
                  onRegenerated={onRegenerated}
                  onError={songProject.setError}
                />
              </section>
            </div>
            <div className="workspace-column">
              <ReferencePanel
                styleTemplateId={styles.selectedStyleId || null}
                styleStrength={styleStrength}
                onGenerated={onGenerateFromReference}
                onError={songProject.setError}
              />
            </div>
          </div>

          <div className="workspace-grid">
            <div className="workspace-column">
              <EvaluationPanel onError={songProject.setError} />
            </div>
            <div className="workspace-column" />
          </div>
        </>
      )}
    </div>
  );
}
