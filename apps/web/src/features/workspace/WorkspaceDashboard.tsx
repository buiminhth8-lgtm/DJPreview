// WorkspaceDashboard：工作台瀑布流总容器（T38-C）。
//
// 设计原则：
// - 首次打开页面时所有核心模块入口常驻显示。
// - 无 song / spec 时，各模块显示 Empty State 占位。
// - 有 song / spec 时，接入现有真实面板（保留全部既有功能，面板仅在安全条件下渲染）。
// - 不直接发 API 请求；请求由各 hook / 面板内部在 songId 可用时发起。
// - 曲式/轨道/Piano Roll 已拆分为独立段（T38-F）。

import type { useAudioAssets, useSongProject, useStyles, useVersions } from "../../hooks";
import type { useSoundfonts } from "../../hooks";
import { exportStems } from "../../api/audioApi";
import type {
  AssetsResponse,
  DiffItem,
  GenerateFromReferenceResponse,
  OptimizeResponse,
  RegenerationResult,
} from "../../api/types";
import { SectionCard } from "../../components/ui";
import QualityReportPanel from "../quality/QualityReportPanel";
import RegenerationPanel from "./RegenerationPanel";
import { EditSongPanel } from "./EditSongPanel";
import EvaluationPanel from "../quality/EvaluationPanel";
import { FormHarmonyPanel } from "../midi/FormHarmonyPanel";
import { GenerateConsole } from "./GenerateConsole";
import GenerationDebugPanel from "./GenerationDebugPanel";
import { MixerPanel } from "../audio/MixerPanel";
import { MusicSpecPanel } from "./MusicSpecPanel";
import { PianoRollPanel } from "../midi/PianoRollPanel";
import { PlaybackDownloadPanel } from "../audio/PlaybackDownloadPanel";
import { ProjectImportExportPanel } from "../export/ProjectImportExportPanel";
import { ProjectOverviewPanel } from "./ProjectOverviewPanel";
import ReferencePanel from "./ReferencePanel";
import { RenderTasksPanel } from "../tasks/RenderTasksPanel";
import { SoundfontPanel } from "../soundfonts/SoundfontPanel";
import { StemsPanel } from "../audio/StemsPanel";
import { TrackInstrumentPanel } from "../midi/TrackInstrumentPanel";
import { VersionPanel } from "../versions/VersionPanel";
import { WarningsPanel } from "./WarningsPanel";
import WorkspaceHeader from "./WorkspaceHeader";
import { WorkspaceSectionPlaceholder } from "./WorkspaceSectionPlaceholder";

export interface WorkspaceDashboardProps {
  songProject: ReturnType<typeof useSongProject>;
  audioAssets: ReturnType<typeof useAudioAssets>;
  versions: ReturnType<typeof useVersions>;
  soundfonts: ReturnType<typeof useSoundfonts>;
  styles: ReturnType<typeof useStyles>;
  styleStrength: number;
  setStyleStrength: (value: number) => void;
  pianoRefreshKey: number;
  lastDiff: DiffItem[] | null;
  onGenerate: () => void;
  onGenerateMidi: () => void;
  onRenderAudio: () => void;
  onApplyEdit: (autoRender?: boolean) => void;
  onLoadVersions: () => void;
  onRestore: (versionId: string) => void;
  onMixApplied: (assets: AssetsResponse) => void;
  onOptimized: (result: OptimizeResponse) => void;
  onRegenerated: (result: RegenerationResult) => void;
  onGenerateFromReference: (result: GenerateFromReferenceResponse) => void;
  onImported: (songId: string) => void;
  onSoundFontChanged: () => void;
}

export default function WorkspaceDashboard({
  songProject,
  audioAssets,
  versions,
  soundfonts,
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
  onSoundFontChanged,
}: WorkspaceDashboardProps) {
  const songId = songProject.songId;
  const spec = songProject.musicSpec;
  const hasSong = Boolean(songId && spec);

  return (
    <div className="workspace-dashboard">
      <div className="workspace-dashboard-inner">
      <WorkspaceHeader
        songId={songId}
        currentVersionId={versions.currentVersionId}
        hasMidi={Boolean(audioAssets.assets?.has_midi)}
        hasAudio={Boolean(audioAssets.assets?.has_audio)}
        error={songProject.error}
      />

      {/* 顶部生成区域：生成控制台 + 当前工程概览 */}
      <div className="workspace-hero-grid">
        <GenerateConsole
          prompt={songProject.prompt}
          onPromptChange={songProject.setPrompt}
          provider={songProject.generationDebug?.provider ?? songProject.generationErrorInfo?.provider}
          model={songProject.generationDebug?.model}
          reasoningEffort={null}
          responseFormatEnabled={null}
          isGeneratingSpec={songProject.loadingSpec}
          isGeneratingMidi={audioAssets.loadingMidi}
          isRenderingAudio={audioAssets.loadingAudio}
          hasMusicSpec={Boolean(spec)}
          hasMidi={Boolean(audioAssets.assets?.has_midi)}
          hasAudio={Boolean(audioAssets.assets?.has_audio)}
          hasSong={Boolean(songId)}
          onGenerateSpec={onGenerate}
          onGenerateMidi={onGenerateMidi}
          onRenderAudio={onRenderAudio}
          lastRequestId={songProject.generationRequestId}
          errorMessage={songProject.error}
          styleId={styles.selectedStyleId}
          styleStrength={styleStrength}
          onStyleChange={(id, strength) => {
            styles.setSelectedStyleId(id);
            setStyleStrength(strength);
          }}
          onError={songProject.setError}
        />
        <ProjectOverviewPanel
          songId={songId}
          currentVersionId={versions.currentVersionId}
          musicSpec={spec}
          warningCount={songProject.validation?.warnings.length ?? 0}
          hasMidi={Boolean(audioAssets.assets?.has_midi)}
          hasAudio={Boolean(audioAssets.assets?.has_audio)}
          lastRequestId={songProject.generationRequestId}
          audioRenderMetadata={audioAssets.audioRenderMetadata}
        />
      </div>

      {/* 瀑布流：所有核心模块常驻 */}
      <div className="workspace-waterfall">
        {/* 播放与下载（分轨 / 音源 / 任务由下方独立段覆盖） */}
        <PlaybackDownloadPanel
          songId={songId}
          midiUrl={hasSong ? audioAssets.midiUrl : null}
          wavUrl={hasSong ? audioAssets.audioStreamUrl : null}
          hasMidi={Boolean(audioAssets.assets?.has_midi) || Boolean(audioAssets.midiResult)}
          hasAudio={Boolean(audioAssets.assets?.has_audio) || Boolean(audioAssets.audioResult)}
          isRenderingAudio={audioAssets.loadingAudio}
          isGeneratingMidi={audioAssets.loadingMidi}
          hasMusicSpec={Boolean(spec)}
          audioRenderMetadata={audioAssets.audioRenderMetadata}
          audioNeedsRender={audioAssets.audioNeedsRender}
          selectedSoundfontName={soundfonts.projectSoundfont?.soundfont?.soundfont_name ?? null}
          onGenerateMidi={onGenerateMidi}
          onRenderAudio={onRenderAudio}
          onDownloadMidi={() => {
            if (audioAssets.midiDownloadUrl) window.open(audioAssets.midiDownloadUrl, "_blank");
          }}
          onDownloadWav={() => {
            if (audioAssets.audioDownloadUrl) window.open(audioAssets.audioDownloadUrl, "_blank");
          }}
        />

        {/* MusicSpec / Warnings / Debug */}
        <MusicSpecPanel musicSpec={spec} requestId={songProject.generationRequestId} />
        <WarningsPanel
          warnings={songProject.generationWarnings}
          hasMusicSpec={Boolean(spec)}
        />
        <GenerationDebugPanel
          status={songProject.generationStatus}
          log={songProject.generationLog}
          requestId={songProject.generationRequestId}
          debug={songProject.generationDebug}
          warnings={songProject.generationWarnings}
          errorInfo={songProject.generationErrorInfo}
          audioRenderMetadata={audioAssets.audioRenderMetadata}
        />

        {/* 曲式与和声 */}
        <FormHarmonyPanel musicSpec={spec} warnings={songProject.generationWarnings} />

        {/* 轨道与乐器 */}
        <TrackInstrumentPanel
          musicSpec={spec}
          warnings={songProject.generationWarnings}
          debug={songProject.generationDebug}
        />

        {/* Piano Roll */}
        <PianoRollPanel
          songId={songId}
          hasMidi={Boolean(audioAssets.assets?.has_midi) || Boolean(audioAssets.midiResult)}
          hasMusicSpec={Boolean(spec)}
          isGeneratingMidi={audioAssets.loadingMidi}
          refreshKey={pianoRefreshKey}
          onGenerateMidi={onGenerateMidi}
          onError={songProject.setError}
        />

        {/* 编曲质量 */}
        {hasSong && songId && spec ? (
          <SectionCard title="编曲质量" description="质量报告与自动优化">
            <QualityReportPanel
              songId={songId}
              onOptimized={onOptimized}
              onError={songProject.setError}
            />
          </SectionCard>
        ) : (
          <WorkspaceSectionPlaceholder
            title="编曲质量"
            description="质量报告与自动优化"
            emptyTitle="暂无质量报告"
            emptyDescription="生成工程后可检查编曲质量并自动优化。"
          />
        )}

        {/* 混音器 */}
        <MixerPanel
          songId={songId}
          musicSpec={spec}
          refreshKey={pianoRefreshKey}
          onApplied={onMixApplied}
          onError={songProject.setError}
        />

        {/* Stems / 分轨导出 */}
        <StemsPanel
          songId={songId}
          hasMidi={Boolean(audioAssets.assets?.has_midi) || Boolean(audioAssets.midiResult)}
          hasAudio={Boolean(audioAssets.assets?.has_audio) || Boolean(audioAssets.audioResult)}
          onError={songProject.setError}
        />

        {/* 版本管理 */}
        <VersionPanel
          songId={songId}
          versions={versions.versions}
          currentVersionId={versions.currentVersionId}
          loading={versions.loadingVersions}
          restoring={versions.restoringVersion}
          selectedDetail={versions.versionDetail}
          selectedDiff={versions.versionDiff}
          onLoad={onLoadVersions}
          onRestore={onRestore}
          onViewDetail={(vid) => void versions.loadVersionDetail(vid)}
          onViewDiff={(vid) => void versions.loadVersionDiff(vid)}
        />

        {/* 自然语言修改 */}
        <EditSongPanel
          songId={songId}
          hasProject={hasSong}
          isEditing={songProject.loadingEdit}
          editError={songProject.error}
          initialInstruction={songProject.editInstruction}
          diff={lastDiff}
          onEditSong={(instruction, options) => {
            songProject.setEditInstruction(instruction);
            onApplyEdit(options?.autoRender ?? false);
          }}
        />

        {/* SoundFont / 音源管理 */}
        <SoundfontPanel
          songId={songId}
          onError={songProject.setError}
          onSoundFontChanged={onSoundFontChanged}
        />

        {/* 工程导入导出 */}
        <ProjectImportExportPanel
          songId={songId}
          hasMidi={Boolean(audioAssets.assets?.has_midi) || Boolean(audioAssets.midiResult)}
          hasAudio={Boolean(audioAssets.assets?.has_audio) || Boolean(audioAssets.audioResult)}
          onImported={onImported}
          onExportProject={() => {
            if (songId) window.open(`/api/v1/songs/${songId}/project/export`, "_blank");
          }}
          onDownloadMidi={() => {
            if (audioAssets.midiDownloadUrl) window.open(audioAssets.midiDownloadUrl, "_blank");
          }}
          onDownloadWav={() => {
            if (audioAssets.audioDownloadUrl) window.open(audioAssets.audioDownloadUrl, "_blank");
          }}
          onExportStems={() => {
            if (songId) {
              exportStems(songId)
                .then(() => audioAssets.refreshAssets())
                .catch((e) => songProject.setError(e instanceof Error ? e.message : String(e)));
            }
          }}
        />

        {/* 任务与日志 */}
        <RenderTasksPanel songId={songId} onError={songProject.setError} />

        {/* 局部重生成 */}
        {hasSong && songId && spec ? (
          <SectionCard title="局部重生成" description="段落 / 轨道 / 整体">
            <RegenerationPanel
              songId={songId}
              spec={spec}
              onRegenerated={onRegenerated}
              onError={songProject.setError}
            />
          </SectionCard>
        ) : (
          <WorkspaceSectionPlaceholder
            title="局部重生成"
            description="段落 / 轨道 / 整体"
            emptyTitle="请先生成或导入工程"
            emptyDescription="创建工程后可对段落、轨道或整体进行重生成。"
          />
        )}

        {/* 参考 MIDI */}
        <SectionCard title="参考 MIDI" description="分析参考 MIDI 并生成新工程">
          <ReferencePanel
            styleTemplateId={styles.selectedStyleId || null}
            styleStrength={styleStrength}
            onGenerated={onGenerateFromReference}
            onError={songProject.setError}
          />
        </SectionCard>

        {/* 批量评估 */}
        <SectionCard title="批量评估" description="内置评估用例">
          <EvaluationPanel onError={songProject.setError} />
        </SectionCard>
      </div>
      </div>
    </div>
  );
}
