// WorkspaceDashboard：工作台瀑布流总容器（T38-C）。
//
// 设计原则：
// - 首次打开页面时所有核心模块入口常驻显示。
// - 无 song / spec 时，各模块显示 Empty State 占位。
// - 有 song / spec 时，接入现有真实面板（保留全部既有功能，面板仅在安全条件下渲染）。
// - 不直接发 API 请求；请求由各 hook / 面板内部在 songId 可用时发起。
// - 曲式/轨道/Piano Roll 当前聚合在「编曲检查」AnalysisPanel 中，T38-F 拆分为独立段。

import type { useAudioAssets, useSongProject, useStyles, useVersions } from "../../hooks";
import type {
  AssetsResponse,
  DiffItem,
  GenerateFromReferenceResponse,
  OptimizeResponse,
  RegenerationResult,
} from "../../api/types";
import { SectionCard } from "../ui";
import RegenerationPanel from "../RegenerationPanel";
import AnalysisPanel from "./AnalysisPanel";
import EditPanel from "./EditPanel";
import EvaluationPanel from "./EvaluationPanel";
import { GenerateConsole } from "./GenerateConsole";
import GenerationDebugPanel from "./GenerationDebugPanel";
import MixerPanel from "./MixerPanel";
import PlayerPanel from "./PlayerPanel";
import { ProjectOverviewPanel } from "./ProjectOverviewPanel";
import ProjectPanel from "./ProjectPanel";
import ReferencePanel from "./ReferencePanel";
import RenderTasksPanel from "./RenderTasksPanel";
import VersionPanel from "./VersionPanel";
import WorkspaceHeader from "./WorkspaceHeader";
import { WorkspaceSectionPlaceholder } from "./WorkspaceSectionPlaceholder";

export interface WorkspaceDashboardProps {
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

export default function WorkspaceDashboard({
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
}: WorkspaceDashboardProps) {
  const songId = songProject.songId;
  const spec = songProject.musicSpec;
  const hasSong = Boolean(songId && spec);

  return (
    <div className="container workspace workspace-dashboard">
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
        />
      </div>

      {/* 瀑布流：所有核心模块常驻 */}
      <div className="workspace-waterfall">
        {/* 播放与下载（含分轨 / 音源 / 异步任务，位于 PlayerPanel 内） */}
        {hasSong && songId ? (
          <SectionCard title="播放与下载" description="MIDI / WAV / 分轨 / 音源 / 异步任务">
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
              onAssetsChanged={() => void audioAssets.refreshAssets()}
              onError={songProject.setError}
            />
          </SectionCard>
        ) : (
          <WorkspaceSectionPlaceholder
            title="播放与下载"
            description="MIDI / WAV / 分轨 / 音源 / 异步任务"
            emptyTitle="暂无可播放音频"
            emptyDescription="生成 MIDI 后可渲染 WAV，渲染完成后可播放和下载。"
          />
        )}

        {/* MusicSpec / Warnings / Debug */}
        {hasSong && spec ? (
          <SectionCard title="MusicSpec / Warnings / Debug" description="生成状态、校验与调试日志">
            <div className="workspace-section-note">
              当前工程：{spec.title} · {spec.tempo?.bpm ?? "?"} BPM ·{" "}
              {spec.tonality ? `${spec.tonality.key} ${spec.tonality.mode}` : "未知调性"}
            </div>
            <GenerationDebugPanel
              status={songProject.generationStatus}
              log={songProject.generationLog}
              requestId={songProject.generationRequestId}
              debug={songProject.generationDebug}
              warnings={songProject.generationWarnings}
              errorInfo={songProject.generationErrorInfo}
            />
          </SectionCard>
        ) : (
          <WorkspaceSectionPlaceholder
            title="MusicSpec / Warnings / Debug"
            description="生成状态、校验与调试日志"
            emptyTitle="暂无 MusicSpec"
            emptyDescription="输入音乐描述并点击生成，或导入 .aimusic.zip 工程。"
          />
        )}

        {/* 编曲检查：曲式与和声 / 轨道与乐器 / Piano Roll / 质量（T38-F 拆分为独立段） */}
        {hasSong && songId && spec ? (
          <SectionCard title="编曲检查" description="曲式 / 轨道 / Piano Roll / 质量">
            <AnalysisPanel
              songId={songId}
              spec={spec}
              refreshKey={pianoRefreshKey}
              onOptimized={onOptimized}
              onError={songProject.setError}
            />
          </SectionCard>
        ) : (
          <WorkspaceSectionPlaceholder
            title="编曲检查（曲式 / 轨道 / Piano Roll / 质量）"
            description="段落、起止小节、和弦、编曲轨道、音符分布"
            emptyTitle="暂无编曲数据"
            emptyDescription="生成 MusicSpec 后将显示曲式、轨道、Piano Roll 与质量报告。"
          />
        )}

        {/* 混音器 */}
        {hasSong && songId ? (
          <SectionCard title="混音器" description="音量 / 声像 / 静音 / 独奏">
            <MixerPanel
              songId={songId}
              refreshKey={pianoRefreshKey}
              onApplied={onMixApplied}
              onError={songProject.setError}
            />
          </SectionCard>
        ) : (
          <WorkspaceSectionPlaceholder
            title="混音器"
            description="音量 / 声像 / 静音 / 独奏"
            emptyTitle="暂无可混音轨道"
            emptyDescription="生成 MusicSpec 后将显示轨道音量、声像、静音和独奏控制。"
          />
        )}

        {/* Stems / 分轨导出 */}
        <WorkspaceSectionPlaceholder
          title="Stems / 分轨导出"
          description="各轨道独立 MIDI / WAV"
          emptyTitle="暂无分轨"
          emptyDescription="渲染音频后可导出分轨。"
        />

        {/* 版本管理 */}
        {hasSong && songId ? (
          <SectionCard title="版本管理" description="版本列表 / 恢复">
            <VersionPanel
              versions={versions.versions}
              currentVersionId={versions.currentVersionId}
              loading={versions.loadingVersions}
              onLoad={onLoadVersions}
              onRestore={onRestore}
            />
          </SectionCard>
        ) : (
          <WorkspaceSectionPlaceholder
            title="版本管理"
            description="版本列表 / 恢复"
            emptyTitle="暂无版本"
            emptyDescription="生成或导入工程后会自动创建 v1。"
          />
        )}

        {/* 自然语言修改 */}
        {hasSong && songId ? (
          <SectionCard title="自然语言修改" description="用一句话修改音乐">
            <EditPanel
              value={songProject.editInstruction}
              loading={songProject.loadingEdit}
              diff={lastDiff}
              onChange={songProject.setEditInstruction}
              onApply={onApplyEdit}
            />
          </SectionCard>
        ) : (
          <WorkspaceSectionPlaceholder
            title="自然语言修改"
            description="用一句话修改音乐"
            emptyTitle="请先生成或导入工程"
            emptyDescription="创建工程后，可输入“让副歌更宏大”等指令修改音乐。"
          />
        )}

        {/* SoundFont / 音源管理 */}
        <WorkspaceSectionPlaceholder
          title="SoundFont / 音源管理"
          description="扫描 / 选择音源"
          emptyTitle="暂无已选择音源"
          emptyDescription="可以扫描本地 SoundFont；生成工程后可应用到当前工程。"
        />

        {/* 工程导入导出 */}
        {hasSong && songId ? (
          <SectionCard title="工程导入导出" description=".aimusic.zip 导入 / 导出">
            <ProjectPanel songId={songId} onImported={onImported} onError={songProject.setError} />
          </SectionCard>
        ) : (
          <WorkspaceSectionPlaceholder
            title="工程导入导出"
            description=".aimusic.zip 导入 / 导出"
            emptyTitle="可以导入 .aimusic.zip 工程"
            emptyDescription="生成或导入工程后，可导出当前工程、MIDI、WAV 和分轨。"
            badgeVariant="info"
          />
        )}

        {/* 任务与调试日志 */}
        {hasSong && songId ? (
          <SectionCard title="任务与调试日志" description="异步任务与请求日志">
            <RenderTasksPanel
              songId={songId}
              onAssetsChanged={() => void audioAssets.refreshAssets()}
              onError={songProject.setError}
            />
          </SectionCard>
        ) : (
          <WorkspaceSectionPlaceholder
            title="任务与调试日志"
            description="异步任务与请求日志"
            emptyTitle="暂无任务或日志"
            emptyDescription="生成、渲染和导出操作的请求日志会显示在这里。"
          />
        )}

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
  );
}
