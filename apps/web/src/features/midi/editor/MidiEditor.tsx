// features/midi/editor/MidiEditor.tsx（T34.6）
// MIDI Editor：组合 TrackSelector + 工具栏（snap/undo/redo/save/discard/zoom/fit/lock）+
// TimelineHeader + PianoKeyboard + PianoRollViewport（可编辑 draft）+ NoteInspector（velocity）。
// Draft 由 useMidiEditorDraft 管理；Save 调 T34.6 API 创建新版本。

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMidiEditorDocument } from "./useMidiEditorDocument";
import { useMidiEditorDraft } from "./useMidiEditorDraft";
import { useMidiViewport } from "./useMidiViewport";
import { useMidiPlayback } from "./useMidiPlayback";
import { saveMidiEditorTrack } from "./midiEditorApi";
import { TrackSelector } from "./TrackSelector";
import { TimelineHeader } from "./TimelineHeader";
import { PianoKeyboard } from "./PianoKeyboard";
import { PianoRollViewport } from "./PianoRollViewport";
import type { MidiEditorDocument, MidiEditorNote, MidiEditorTrack } from "./midiEditorTypes";
import { computePitchRange, DEFAULT_LAYOUT, tickToBar, tickToBeat, ticksPerBar } from "./midiEditorLayout";
import { DEFAULT_SNAP, SNAP_OPTIONS, midiPitchToNoteName, type SnapValue } from "./midiEditorGeometry";
import { ActionButton, EmptyState, ErrorState, InlineNotice, LoadingState, SectionCard } from "../../../components/ui";
import { getErrorMessage } from "../../../hooks/error";

export interface MidiEditorProps {
  songId?: string | null;
  refreshKey?: number;
  onSaved?: (versionId: string) => void;
}

function defaultTrackId(doc: MidiEditorDocument): string | null {
  if (!doc.tracks.length) return null;
  const firstWithNotes = doc.tracks.find((t) => t.notes.length > 0);
  return (firstWithNotes ?? doc.tracks[0]).id;
}

function isEditableTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el) return false;
  return (
    el.tagName === "INPUT" ||
    el.tagName === "TEXTAREA" ||
    el.tagName === "SELECT" ||
    el.isContentEditable
  );
}

export function MidiEditor({ songId, refreshKey = 0, onSaved }: MidiEditorProps) {
  const { document, isLoading, error, notFound, reload } = useMidiEditorDocument(songId);
  const draft = useMidiEditorDraft(document);
  const viewport = useMidiViewport();
  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(null);
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [snap, setSnap] = useState<SnapValue>(DEFAULT_SNAP);
  const [lockedTrackIds, setLockedTrackIds] = useState<Set<string>>(new Set());
  const [spacePressed, setSpacePressed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<{ currentVersionId: string; baseVersionId: string } | null>(null);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const dirtyRef = useRef(false);
  const playback = useMidiPlayback({
    songId,
    document,
    draftNotesByTrack: draft.draftNotesByTrack,
    selectedTrackId,
  });
  const stopPreview = playback.stop;
  const layout = useMemo(
    () => ({
      pixelsPerTick: viewport.pixelsPerTick,
      rowHeight: viewport.rowHeight,
      keyboardWidth: DEFAULT_LAYOUT.keyboardWidth,
    }),
    [viewport.pixelsPerTick, viewport.rowHeight],
  );

  // songId 或 document 变化：重选有效轨道、清空 note 选择（draft hook 已自行重置）
  useEffect(() => {
    setSelectedNoteId(null);
    setLockedTrackIds(new Set());
    viewport.resetZoom();
    setSaveError(null);
    setConflict(null);
    setConfirmDiscard(false);
    if (!document) {
      setSelectedTrackId(null);
      return;
    }
    setSelectedTrackId((prev) => {
      if (prev && document.tracks.some((t) => t.id === prev)) return prev;
      return defaultTrackId(document);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [document]);

  // 同步 dirtyRef（beforeunload / 离开守卫用）
  useEffect(() => {
    dirtyRef.current = draft.dirtyTracks.size > 0;
  }, [draft.dirtyTracks]);

  // beforeunload：仅 dirty 时注册
  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!dirtyRef.current) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, []);

  // Undo/Redo 快捷键（Ctrl/Cmd+Z、Ctrl/Cmd+Shift+Z、Ctrl+Y）；输入框聚焦时不触发
  // 放在 selectedTrack 声明之后，见下方。

  // refreshKey 变化（MIDI 重新生成 / 版本恢复）→ 重新加载 document
  useEffect(() => {
    if (refreshKey > 0) {
      stopPreview();
      void reload();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey, stopPreview]);

  // Space 键 → pan 模式（松开时结束）
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.code === "Space" && !isEditableTarget(e.target)) {
        e.preventDefault();
        setSpacePressed(true);
      }
    };
    const up = (e: KeyboardEvent) => {
      if (e.code === "Space") setSpacePressed(false);
    };
    const blur = () => setSpacePressed(false);
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    window.addEventListener("blur", blur);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
      window.removeEventListener("blur", blur);
    };
  }, []);

  const selectedTrack: MidiEditorTrack | null = useMemo(() => {
    if (!document) return null;
    return document.tracks.find((t) => t.id === selectedTrackId) ?? null;
  }, [document, selectedTrackId]);

  // Undo/Redo 快捷键（需在 selectedTrack 声明之后）
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isEditableTarget(e.target)) return;
      if (!selectedTrack) return;
      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) draft.redo(selectedTrack.id);
        else draft.undo(selectedTrack.id);
      } else if (mod && e.key.toLowerCase() === "y") {
        e.preventDefault();
        draft.redo(selectedTrack.id);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedTrack, draft]);

  // 当前轨道 draft notes（未编辑则 fallback 到 document notes）
  const trackDraftNotes: MidiEditorNote[] = useMemo(() => {
    if (!selectedTrack) return [];
    const draftNotes = draft.draftNotesByTrack[selectedTrack.id];
    return draftNotes ?? selectedTrack.notes;
  }, [selectedTrack, draft.draftNotesByTrack]);

  const selectedNote: MidiEditorNote | null = useMemo(
    () => trackDraftNotes.find((n) => n.id === selectedNoteId) ?? null,
    [trackDraftNotes, selectedNoteId],
  );

  const pitchRange = useMemo(
    () =>
      trackDraftNotes.length
        ? computePitchRange(trackDraftNotes)
        : {
            minPitch: selectedTrack?.channel === 9 ? 36 : 48,
            maxPitch: selectedTrack?.channel === 9 ? 60 : 84,
          },
    [selectedTrack?.channel, trackDraftNotes],
  );

  const isTrackLocked = selectedTrack ? lockedTrackIds.has(selectedTrack.id) : false;

  const toggleTrackLock = () => {
    if (!selectedTrack) return;
    setLockedTrackIds((prev) => {
      const next = new Set(prev);
      if (next.has(selectedTrack.id)) next.delete(selectedTrack.id);
      else next.add(selectedTrack.id);
      return next;
    });
  };

  const meter = useMemo(
    () => ({
      numerator: document?.timeSignature?.[0] ?? 4,
      denominator: document?.timeSignature?.[1] ?? 4,
    }),
    [document?.timeSignature],
  );
  const songMaxTick = playback.maxTick;
  const perBar = document ? ticksPerBar(document.ppq, meter) : 1;

  // 删除选中 Note（Delete/Backspace，非输入框内；locked 时不删除）
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!selectedTrack || !selectedNoteId || isTrackLocked) return;
      if (isEditableTarget(e.target)) return;
      if (e.key === "Delete" || e.key === "Backspace") {
        e.preventDefault();
        draft.deleteNote(selectedTrack.id, selectedNoteId);
        setSelectedNoteId(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedTrack, selectedNoteId, isTrackLocked, draft]);

  const handleVelocityCommit = (value: number) => {
    if (!selectedTrack || !selectedNoteId || isTrackLocked) return;
    const clamped = Math.max(1, Math.min(127, Math.round(value)));
    draft.setVelocity(selectedTrack.id, selectedNoteId, clamped);
  };

  const handleFit = () => {
    if (!document || !selectedTrack) return;
    const container = viewportRef.current;
    const w = container?.clientWidth ?? 800;
    const h = container?.clientHeight ?? 300;
    viewport.fitTrack(trackDraftNotes, document.ppq, meter, w, h);
  };

  // 供 fit 使用的容器 ref
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const gridScrollRef = useRef<HTMLDivElement | null>(null);
  const timelineScrollRef = useRef<HTMLDivElement | null>(null);
  const keyboardScrollRef = useRef<HTMLDivElement | null>(null);

  // Roll 是滚动源；Timeline/Keyboard 跟随同一 viewport state。
  useEffect(() => {
    if (gridScrollRef.current && gridScrollRef.current.scrollLeft !== viewport.scrollLeft) {
      gridScrollRef.current.scrollLeft = viewport.scrollLeft;
    }
    if (gridScrollRef.current && gridScrollRef.current.scrollTop !== viewport.scrollTop) {
      gridScrollRef.current.scrollTop = viewport.scrollTop;
    }
    if (timelineScrollRef.current && timelineScrollRef.current.scrollLeft !== viewport.scrollLeft) {
      timelineScrollRef.current.scrollLeft = viewport.scrollLeft;
    }
    if (keyboardScrollRef.current && keyboardScrollRef.current.scrollTop !== viewport.scrollTop) {
      keyboardScrollRef.current.scrollTop = viewport.scrollTop;
    }
  }, [viewport.scrollLeft, viewport.scrollTop]);

  const handleAddNote = useCallback(
    (note: Omit<MidiEditorNote, "id">) => {
      if (selectedTrackId) draft.addNote(selectedTrackId, note);
    },
    [draft.addNote, selectedTrackId],
  );
  const handleMoveNote = useCallback(
    (noteId: string, start: number, pitch: number) => {
      if (selectedTrackId) draft.moveNote(selectedTrackId, noteId, start, pitch);
    },
    [draft.moveNote, selectedTrackId],
  );
  const handleResizeNote = useCallback(
    (noteId: string, duration: number) => {
      if (selectedTrackId) draft.resizeNote(selectedTrackId, noteId, duration);
    },
    [draft.resizeNote, selectedTrackId],
  );
  const handleDragEnd = useCallback(() => {
    if (selectedTrackId) draft.commitEdit(selectedTrackId);
  }, [draft.commitEdit, selectedTrackId]);
  const handleGridRef = useCallback(
    (element: HTMLDivElement | null) => {
      gridScrollRef.current = element;
      if (element) {
        element.scrollLeft = viewport.scrollLeft;
        element.scrollTop = viewport.scrollTop;
      }
    },
    [viewport.scrollLeft, viewport.scrollTop],
  );
  const handleRollZoom = useCallback(
    (direction: 1 | -1) => (direction > 0 ? viewport.zoomHIn() : viewport.zoomHOut()),
    [viewport.zoomHIn, viewport.zoomHOut],
  );

  const handleSave = useCallback(async () => {
    if (!document || !selectedTrack || saving) return;
    const notes = draft.draftNotesByTrack[selectedTrack.id];
    if (!notes) return;
    stopPreview();
    setSaving(true);
    setSaveError(null);
    setConflict(null);
    try {
      const result = await saveMidiEditorTrack(songId ?? "", {
        trackId: selectedTrack.id,
        baseVersionId: document.versionId,
        notes,
      });
      // Save 成功后：reload document（后端 canonical notes + 新 version）
      await reload();
      onSaved?.(result.versionId);
    } catch (e) {
      const err = e as { status?: number; details?: Record<string, unknown>; code?: string };
      if (err.status === 409) {
        setConflict({
          currentVersionId: String(err.details?.current_version_id ?? "?") ,
          baseVersionId: String(err.details?.base_version_id ?? "?"),
        });
      } else {
        setSaveError(getErrorMessage(e));
      }
    } finally {
      setSaving(false);
    }
  }, [document, selectedTrack, draft, songId, saving, reload, onSaved, stopPreview]);

  const handleDiscard = () => {
    if (!selectedTrack) return;
    draft.discardTrack(selectedTrack.id);
    setSelectedNoteId(null);
    setConfirmDiscard(false);
    setSaveError(null);
  };

  let body;
  if (isLoading && !document) {
    body = <LoadingState title="正在加载 MIDI…" />;
  } else if (notFound && !document) {
    body = (
      <EmptyState
        title="尚未生成 MIDI"
        description="生成 MIDI 后即可在 Piano Roll 中查看和编辑各轨道。"
      />
    );
  } else if (error && !document) {
    body = (
      <ErrorState
        title="MIDI 加载失败"
        message={error}
        action={<button onClick={() => void reload()}>重新加载</button>}
      />
    );
  } else if (!document || !selectedTrack) {
    body = <EmptyState title="暂无 MIDI 数据" description="生成 MIDI 后即可查看。" />;
  } else {
    const isDirty = draft.dirtyTracks.has(selectedTrack.id);
    body = (
      <div className="midi-editor">
        <TrackSelector
          tracks={document.tracks}
          selectedTrackId={selectedTrack.id}
          onSelect={setSelectedTrackId}
        />

        <div className="midi-editor__toolbar">
          <span className="midi-editor__transport">
            <ActionButton
              variant="primary"
              onClick={() => void playback.play()}
              disabled={playback.isPlaying || playback.isPreparing || document.bpm == null}
              loading={playback.isPreparing}
            >
              {playback.isPreparing ? "准备试听…" : "▶ Play"}
            </ActionButton>
            <ActionButton
              variant="secondary"
              onClick={playback.stop}
              disabled={!playback.isPlaying && !playback.isPreparing}
            >
              ■ Stop
            </ActionButton>
          </span>

          <label className="midi-editor__preview-scope">
            Preview
            <select
              value={playback.scope}
              onChange={(event) => playback.setScope(event.target.value as "current_track" | "all_tracks")}
              disabled={playback.isPlaying || playback.isPreparing}
              aria-label="Preview 范围"
            >
              <option value="current_track">Current Track</option>
              <option value="all_tracks">All Tracks</option>
            </select>
          </label>

          <span className="midi-editor__loop-controls">
            <label>
              <input
                type="checkbox"
                checked={playback.loopEnabled}
                onChange={(event) => playback.setLoopEnabled(event.target.checked)}
                aria-label="Loop 开关"
              />
              Loop
            </label>
            <label>
              Start bar
              <input
                type="number"
                min={1}
                max={Math.max(1, Math.ceil(songMaxTick / perBar))}
                value={Math.floor(playback.loopStartTick / perBar) + 1}
                onChange={(event) => playback.setLoopStartTick((Math.max(1, Number(event.target.value)) - 1) * perBar)}
                aria-label="Loop Start bar"
              />
            </label>
            <label>
              End bar
              <input
                type="number"
                min={1}
                max={Math.max(2, Math.ceil(songMaxTick / perBar) + 1)}
                value={Math.floor(playback.loopEndTick / perBar) + 1}
                onChange={(event) => playback.setLoopEndTick((Math.max(1, Number(event.target.value)) - 1) * perBar)}
                aria-label="Loop End bar"
              />
            </label>
          </span>

          <label className="midi-editor__snap">
            Snap
            <select
              value={snap}
              onChange={(e) => setSnap(e.target.value as SnapValue)}
              aria-label="Snap 吸附"
            >
              {SNAP_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt === "off" ? "Off" : opt}
                </option>
              ))}
            </select>
          </label>

          <span className="midi-editor__history">
            <ActionButton variant="ghost" onClick={() => draft.undo(selectedTrack.id)} disabled={!draft.canUndoTrack(selectedTrack.id)} title="撤销 (Ctrl+Z)">
              Undo
            </ActionButton>
            <ActionButton variant="ghost" onClick={() => draft.redo(selectedTrack.id)} disabled={!draft.canRedoTrack(selectedTrack.id)} title="重做 (Ctrl+Shift+Z)">
              Redo
            </ActionButton>
          </span>

          <button type="button" className="ui-action-button ui-action-button--secondary" onClick={toggleTrackLock} aria-pressed={isTrackLocked}>
            {isTrackLocked ? "🔒 已锁定" : "🔓 编辑"}
          </button>

          {isDirty && <span className="status-chip status-warning">● 未保存修改</span>}

          <span className="midi-editor__save">
            <ActionButton
              variant="primary"
              onClick={() => void handleSave()}
              disabled={!isDirty || saving || !document?.versionId}
              loading={saving}
            >
              {saving ? "保存中…" : "保存 MIDI 修改"}
            </ActionButton>
            <ActionButton variant="ghost" onClick={() => setConfirmDiscard(true)} disabled={!isDirty}>
              放弃修改
            </ActionButton>
          </span>

          <span className="midi-editor__zoom">
            <button type="button" onClick={viewport.zoomHOut} aria-label="横向缩小">−</button>
            <span className="midi-editor__zoom-label">H {viewport.horizontalPercent}%</span>
            <button type="button" onClick={viewport.zoomHIn} aria-label="横向放大">＋</button>
          </span>
          <span className="midi-editor__zoom">
            <button type="button" onClick={viewport.zoomVOut} aria-label="纵向缩小">V−</button>
            <span className="midi-editor__zoom-label">Row {viewport.rowHeight}px</span>
            <button type="button" onClick={viewport.zoomVIn} aria-label="纵向放大">V＋</button>
          </span>
          <button type="button" className="ui-action-button ui-action-button--ghost" onClick={handleFit}>
            Fit
          </button>

          {isDirty && <span className="status-chip status-warning">未保存草稿</span>}
          <span className={`status-chip ${playback.isPlaying ? "status-ok" : ""}`}>
            Editor Preview · tick {Math.round(playback.currentTick)}
          </span>
          <span className="midi-editor__toolbar-hint">
            时间轴点击定位 · Ctrl+滚轮缩放 · Shift+滚轮横滚 · Space+拖动平移 · 双击添加 · 右边缘拉长 · Delete 删除
          </span>
        </div>

        <div className="midi-editor__board" ref={viewportRef}>
          <div className="midi-editor__timeline-row">
            <div className="midi-editor__timeline-spacer" style={{ width: DEFAULT_LAYOUT.keyboardWidth }} />
            <div
              className="midi-editor__timeline-scroll"
              ref={timelineScrollRef}
              onScroll={(event) => viewport.setScrollLeft(event.currentTarget.scrollLeft)}
            >
              <TimelineHeader
                ppq={document.ppq}
                meter={meter}
                maxTick={Math.max(songMaxTick, 0)}
                pixelsPerTick={layout.pixelsPerTick}
                currentTick={playback.currentTick}
                loopEnabled={playback.loopEnabled}
                loopStartTick={playback.loopStartTick}
                loopEndTick={playback.loopEndTick}
                onSeek={playback.seek}
              />
            </div>
          </div>
          <div className="midi-editor__roll-row">
            <div
              className="midi-editor__keyboard-scroll"
              ref={keyboardScrollRef}
              onScroll={(event) => viewport.setScrollTop(event.currentTarget.scrollTop)}
            >
              <PianoKeyboard
                minPitch={pitchRange.minPitch}
                maxPitch={pitchRange.maxPitch}
                rowHeight={layout.rowHeight}
              />
            </div>
            <div className="midi-editor__viewport-scroll">
              <PianoRollViewport
                notes={trackDraftNotes}
                ppq={document.ppq}
                meter={meter}
                bpm={document.bpm}
                channel={selectedTrack.channel}
                isDrum={selectedTrack.isDrum}
                snap={snap}
                selectedNoteId={selectedNoteId}
                locked={isTrackLocked}
                panEnabled={spacePressed}
                onSelectNote={setSelectedNoteId}
                onAddNote={handleAddNote}
                onMoveNote={handleMoveNote}
                onResizeNote={handleResizeNote}
                onDragEnd={handleDragEnd}
                onZoomH={handleRollZoom}
                onScrollLeftChange={viewport.setScrollLeft}
                onScrollTopChange={viewport.setScrollTop}
                gridRef={handleGridRef}
                currentTick={playback.currentTick}
                loopEnabled={playback.loopEnabled}
                loopStartTick={playback.loopStartTick}
                loopEndTick={playback.loopEndTick}
                layout={layout}
              />
            </div>
          </div>
        </div>

        <div className="midi-editor__footer">
          <span>Track: {selectedTrack.name}</span>
          <span>Notes: {trackDraftNotes.length}</span>
          <span>PPQ: {document.ppq}</span>
          <span>Playhead: {Math.round(playback.currentTick)} tick</span>
          <span>Version: {document.versionId ?? "—"}</span>
          {selectedNote && (
            <span className="midi-editor__selected-note">
              {midiPitchToNoteName(selectedNote.pitch)} ({selectedNote.pitch}) · bar{" "}
              {tickToBar(selectedNote.startTick, document.ppq, meter)} · beat{" "}
              {tickToBeat(selectedNote.startTick, document.ppq).toFixed(2)}
            </span>
          )}
        </div>

        {selectedNote && selectedTrack && (
          <div className="midi-editor__inspector">
            <label className="midi-editor__velocity">
              Velocity
              <input
                type="number"
                min={1}
                max={127}
                value={selectedNote.velocity}
                disabled={isTrackLocked}
                onChange={(e) => {
                  const v = Number(e.target.value);
                  if (!Number.isNaN(v)) handleVelocityCommit(v);
                }}
                aria-label="Velocity 力度"
              />
            </label>
          </div>
        )}

        {saveError && (
          <InlineNotice variant="danger" title="保存失败">
            {saveError}
          </InlineNotice>
        )}

        {playback.error && (
          <InlineNotice variant="danger" title="Editor Preview 失败">
            {playback.error}
          </InlineNotice>
        )}

        {playback.warnings.length > 0 && (
          <InlineNotice variant="warning" title="Editor Preview">
            {playback.warnings.join("；")}
          </InlineNotice>
        )}

        {conflict && (
          <div className="ui-dialog-backdrop" role="presentation" onMouseDown={(e) => e.target === e.currentTarget && setConflict(null)}>
            <div className="ui-dialog" role="dialog" aria-modal="true">
              <h2 className="ui-dialog__title">版本冲突</h2>
              <p className="ui-dialog__body">
                工程已更新到 {conflict.currentVersionId}，当前 MIDI 草稿基于 {conflict.baseVersionId}，无法直接保存。
              </p>
              <div className="ui-dialog__actions ui-button-row">
                <ActionButton variant="secondary" onClick={() => setConflict(null)}>继续查看草稿</ActionButton>
                <ActionButton variant="primary" onClick={() => void reload()}>重新加载最新版本</ActionButton>
              </div>
            </div>
          </div>
        )}

        {confirmDiscard && (
          <div className="ui-dialog-backdrop" role="presentation" onMouseDown={(e) => e.target === e.currentTarget && setConfirmDiscard(false)}>
            <div className="ui-dialog" role="dialog" aria-modal="true">
              <h2 className="ui-dialog__title">放弃修改？</h2>
              <p className="ui-dialog__body">放弃当前未保存的 MIDI 修改？此操作无法撤销。</p>
              <div className="ui-dialog__actions ui-button-row">
                <ActionButton variant="secondary" onClick={() => setConfirmDiscard(false)}>取消</ActionButton>
                <ActionButton variant="danger" onClick={handleDiscard}>放弃修改</ActionButton>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <SectionCard
      title="MIDI Editor"
      description="轨道选择与音符编辑（草稿）"
      badge={document ? <span className="status-chip status-ok">{document.tracks.length} tracks</span> : undefined}
    >
      {body}
    </SectionCard>
  );
}
