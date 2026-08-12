// ProjectWorkspacePage：/projects/:songId 工程工作台页（T33.5 独立版）。
// songId 必须来自 URL；页面级 loading / 404 / error 处理；
// 工作台数据经 useProjectWorkspace(songId) 协调（useProject + 业务 hooks）。

import { Link, useBlocker, useNavigate, useParams } from "react-router-dom";
import { useCallback, useState } from "react";
import { useProjectWorkspace } from "../features/workspace/useProjectWorkspace";
import WorkspaceHeader from "../features/workspace/WorkspaceHeader";
import WorkspaceDashboard from "../features/workspace/WorkspaceDashboard";
import { DeleteProjectDialog } from "../features/projects/DeleteProjectDialog";
import { deleteProject } from "../features/projects/projectApi";
import { ErrorState, LoadingState } from "../components/ui";
import type { AssetsResponse, DiffItem, GenerateFromReferenceResponse, OptimizeResponse, RegenerationResult } from "../api/types";
import { ActionButton } from "../components/ui";

interface PendingMidiMutation {
  label: string;
  action: () => void;
}

export default function ProjectWorkspacePage() {
  const { songId } = useParams<{ songId: string }>();
  const navigate = useNavigate();
  const ws = useProjectWorkspace(songId);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [midiDraftDirty, setMidiDraftDirty] = useState(false);
  const [midiEditorSessionKey, setMidiEditorSessionKey] = useState(0);
  const [pendingMidiMutation, setPendingMidiMutation] = useState<PendingMidiMutation | null>(null);
  const navigationBlocker = useBlocker(midiDraftDirty);

  const requestMidiMutation = useCallback((label: string, action: () => void) => {
    if (midiDraftDirty) {
      setPendingMidiMutation({ label, action });
      return;
    }
    action();
  }, [midiDraftDirty]);

  const discardDraftAndRun = () => {
    const pending = pendingMidiMutation;
    if (!pending) return;
    setPendingMidiMutation(null);
    setMidiDraftDirty(false);
    setMidiEditorSessionKey((key) => key + 1);
    pending.action();
  };

  const discardDraftAndNavigate = () => {
    setMidiDraftDirty(false);
    navigationBlocker.proceed?.();
  };

  const handleRequestDelete = () => {
    setDeleteOpen(true);
    setDeleteError(null);
    setIsDeleting(false);
  };

  const handleCancelDelete = () => {
    if (isDeleting) return;
    setDeleteOpen(false);
    setDeleteError(null);
  };

  const handleConfirmDelete = async () => {
    if (!songId || isDeleting) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await deleteProject(songId);
      // 清理当前 Workspace 状态（polling / 资产 / 版本）后离开
      ws.songProject.resetProject();
      ws.audioAssets.resetAssets();
      ws.versions.resetVersions();
      navigate("/projects", { replace: true });
    } catch (e) {
      setDeleteError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsDeleting(false);
    }
  };

  if (!songId) {
    return (
      <div className="page page--workspace">
        <ErrorState
          title="缺少工程 ID"
          message="URL 中没有有效的 songId（/projects/:songId）。"
          action={
            <Link to="/projects" className="ui-action-button ui-action-button--secondary">
              返回工程库
            </Link>
          }
        />
      </div>
    );
  }

  if (ws.projectNotFound) {
    return (
      <div className="page page--workspace">
        <ErrorState
          title="工程不存在或已被删除"
          message="找不到该 songId 对应的工程。"
          action={
            <Link to="/projects" className="ui-action-button ui-action-button--secondary">
              返回工程库
            </Link>
          }
        />
      </div>
    );
  }

  if (ws.projectIsLoading && !ws.songProject.musicSpec) {
    return (
      <div className="page page--workspace">
        <LoadingState title="正在加载工程…" />
      </div>
    );
  }

  if (ws.projectError && !ws.songProject.musicSpec) {
    return (
      <div className="page page--workspace">
        <ErrorState
          title="工程加载失败"
          message={ws.projectError}
          action={
            <button onClick={() => void ws.reloadProject()}>重新加载</button>
          }
        />
      </div>
    );
  }

  const { songProject, audioAssets, versions, soundfonts, styles } = ws;
  const lastDiff = null as DiffItem[] | null;
  const projectTitle = songProject.musicSpec?.title ?? null;
  const rendererMeta = audioAssets.audioRenderMetadata;

  const loadProject = (newSongId: string) => {
    navigate(`/projects/${encodeURIComponent(newSongId)}`);
  };

  const handleGenerate = () => {
    requestMidiMutation("生成新工程", () => void (async () => {
      audioAssets.resetAssets();
      versions.resetVersions();
      const result = await songProject.generate(songProject.prompt, styles.selectedStyleId, ws.styleStrength);
      if (result?.song_id) {
        navigate(`/projects/${encodeURIComponent(result.song_id)}`);
      }
    })());
  };

  const handleGenerateMidi = () => {
    requestMidiMutation("重新生成 MIDI", () => {
      void (async () => {
        const result = await audioAssets.generateMidi();
        if (result) ws.handleMidiRegenerated();
      })();
    });
  };
  const handleRenderAudio = () => void audioAssets.renderAudio();
  const handleMidiSaved = () => {
    // MIDI 保存成功 → 标记 WAV stale + 刷新版本/资产
    ws.handleMidiRegenerated();
    void audioAssets.refreshAssets();
    void versions.refreshVersions();
  };

  const handleApplyEdit = (instruction: string, autoRender = true) => {
    requestMidiMutation("AI 修改工程", () => void (async () => {
      const result = await songProject.edit(instruction, autoRender);
      if (!result) return;
      audioAssets.updateFromAssets(result.assets);
      if (result.audio_rendered) audioAssets.clearAudioStale();
      else audioAssets.markAudioStale();
      await versions.refreshVersions();
      ws.refreshPiano();
    })());
  };

  const handleLoadVersions = () => void versions.refreshVersions();

  const handleRestore = (versionId: string) => {
    if (!midiDraftDirty && !window.confirm("确认恢复到该版本？")) return;
    requestMidiMutation("恢复版本", () => void (async () => {
      const result = await versions.restoreVersion(versionId);
      if (!result) return;
      songProject.setMusicSpec(result.music_spec);
      audioAssets.updateFromAssets(result.assets);
      await versions.refreshVersions();
      ws.refreshPiano();
    })());
  };

  const handleMixApplied = (assets: AssetsResponse) => {
    audioAssets.updateFromAssets(assets);
    ws.refreshPiano();
  };

  const handleOptimized = (result: OptimizeResponse) => {
    void (async () => {
      songProject.setMusicSpec(result.music_spec);
      audioAssets.updateFromAssets(result.assets);
      await versions.refreshVersions();
      ws.refreshPiano();
    })();
  };

  const handleRegenerated = (result: RegenerationResult) => {
    void (async () => {
      songProject.setMusicSpec(result.music_spec);
      audioAssets.updateFromAssets(result.assets);
      await versions.refreshVersions();
      ws.refreshPiano();
    })();
  };

  const handleGenerateFromReference = (result: GenerateFromReferenceResponse) => loadProject(result.song_id);
  const handleImported = (newSongId: string) => loadProject(newSongId);

  return (
    <div className="page page--workspace">
      <WorkspaceHeader
        songId={songId}
        title={projectTitle}
        currentVersionId={versions.currentVersionId}
        hasMidi={Boolean(audioAssets.assets?.has_midi)}
        hasAudio={Boolean(audioAssets.assets?.has_audio)}
        audioNeedsRender={audioAssets.audioNeedsRender}
        renderer={rendererMeta?.renderer ?? null}
        isFallback={Boolean(rendererMeta?.isFallback)}
        soundfontName={rendererMeta?.soundfontName ?? null}
        error={songProject.error}
      />
      <WorkspaceDashboard
        songProject={songProject}
        audioAssets={audioAssets}
        versions={versions}
        soundfonts={soundfonts}
        styles={styles}
        styleStrength={ws.styleStrength}
        setStyleStrength={ws.setStyleStrength}
        pianoRefreshKey={ws.pianoRefreshKey}
        midiEditorSessionKey={midiEditorSessionKey}
        lastDiff={lastDiff}
        onGenerate={handleGenerate}
        onGenerateMidi={handleGenerateMidi}
        onRenderAudio={handleRenderAudio}
        onApplyEdit={(instruction, autoRender) => handleApplyEdit(instruction, autoRender)}
        onLoadVersions={handleLoadVersions}
        onRestore={(versionId) => handleRestore(versionId)}
        onMixApplied={handleMixApplied}
        onOptimized={(result) => handleOptimized(result)}
        onRegenerated={(result) => handleRegenerated(result)}
        onGenerateFromReference={handleGenerateFromReference}
        onImported={handleImported}
        onSoundFontChanged={ws.handleSoundFontChanged}
        onMidiSaved={handleMidiSaved}
        onMidiDirtyChange={setMidiDraftDirty}
        onRequestMidiMutation={requestMidiMutation}
        onDeleteProject={handleRequestDelete}
      />
      {navigationBlocker.state === "blocked" && (
        <div className="ui-dialog-backdrop" role="presentation">
          <div className="ui-dialog" role="dialog" aria-modal="true" aria-labelledby="midi-navigation-guard-title">
            <h2 id="midi-navigation-guard-title" className="ui-dialog__title">保留 MIDI 草稿？</h2>
            <p className="ui-dialog__body">当前有未保存的 MIDI 修改。继续离开会放弃这些草稿。</p>
            <div className="ui-dialog__actions ui-button-row">
              <ActionButton variant="secondary" onClick={() => navigationBlocker.reset?.()}>继续编辑</ActionButton>
              <ActionButton variant="danger" onClick={discardDraftAndNavigate}>放弃草稿并离开</ActionButton>
            </div>
          </div>
        </div>
      )}
      {pendingMidiMutation && (
        <div className="ui-dialog-backdrop" role="presentation">
          <div className="ui-dialog" role="dialog" aria-modal="true" aria-labelledby="midi-mutation-guard-title">
            <h2 id="midi-mutation-guard-title" className="ui-dialog__title">放弃 MIDI 草稿？</h2>
            <p className="ui-dialog__body">{pendingMidiMutation.label}会替换当前 MIDI。请选择继续编辑或放弃草稿后继续。</p>
            <div className="ui-dialog__actions ui-button-row">
              <ActionButton variant="secondary" onClick={() => setPendingMidiMutation(null)}>继续编辑</ActionButton>
              <ActionButton variant="danger" onClick={discardDraftAndRun}>放弃草稿并继续</ActionButton>
            </div>
          </div>
        </div>
      )}
      <DeleteProjectDialog
        open={deleteOpen}
        project={
          songId
            ? {
                songId,
                title: projectTitle ?? "未命名工程",
                createdAt: null,
                currentVersionId: versions.currentVersionId ?? null,
                hasMidi: Boolean(audioAssets.assets?.has_midi),
                hasAudio: Boolean(audioAssets.assets?.has_audio),
                hasStems: Boolean(audioAssets.assets?.has_stems),
                hasQualityReport: false,
                renderer: rendererMeta?.renderer ?? null,
                soundfontName: rendererMeta?.soundfontName ?? null,
              }
            : null
        }
        isDeleting={isDeleting}
        error={deleteError}
        onCancel={handleCancelDelete}
        onConfirm={() => void handleConfirmDelete()}
      />
    </div>
  );
}
