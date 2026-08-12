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
import { DEFAULT_SNAP, SNAP_OPTIONS, midiPitchToNoteName, snapTick, type SnapValue } from "./midiEditorGeometry";
import {
  applySelection,
  createMidiClipboard,
  duplicateNotes,
  materializeClipboard,
  summarizeSelectedNotes,
  type MidiClipboard,
  type SelectionIntent,
} from "./midiSelection";
import { ActionButton, EmptyState, ErrorState, InlineNotice, LoadingState, SectionCard } from "../../../components/ui";
import { getErrorMessage } from "../../../hooks/error";
import type { MusicSpec } from "../../../api/types";
import {
  bassOverlapWarning,
  buildMidiEditorMusicContext,
  computeDrumPitchRange,
} from "./midiEditorMusicContext";

export interface MidiEditorProps {
  songId?: string | null;
  refreshKey?: number;
  onSaved?: (versionId: string) => void;
  onDirtyChange?: (dirty: boolean) => void;
  musicSpec?: MusicSpec | null;
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

export function MidiEditor({
  songId,
  refreshKey = 0,
  onSaved,
  onDirtyChange,
  musicSpec = null,
}: MidiEditorProps) {
  const { document, isLoading, error, notFound, reload } = useMidiEditorDocument(songId);
  const draft = useMidiEditorDraft(document);
  const viewport = useMidiViewport();
  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(null);
  const [selectedNoteIds, setSelectedNoteIds] = useState<Set<string>>(new Set());
  const [snap, setSnap] = useState<SnapValue>(DEFAULT_SNAP);
  const [lockedTrackIds, setLockedTrackIds] = useState<Set<string>>(new Set());
  const [spacePressed, setSpacePressed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<{ currentVersionId: string; baseVersionId: string } | null>(null);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const [selectionNotice, setSelectionNotice] = useState<string | null>(null);
  const [showScale, setShowScale] = useState(true);
  const [showChords, setShowChords] = useState(true);
  const [showSections, setShowSections] = useState(true);
  const [loadedContextRefreshKey, setLoadedContextRefreshKey] = useState(refreshKey);
  const dirtyRef = useRef(false);
  const editorRootRef = useRef<HTMLDivElement | null>(null);
  const editorActiveRef = useRef(false);
  const clipboardRef = useRef<MidiClipboard | null>(null);
  const onDirtyChangeRef = useRef(onDirtyChange);
  onDirtyChangeRef.current = onDirtyChange;
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
    setSelectedNoteIds(new Set());
    setLockedTrackIds(new Set());
    viewport.resetZoom();
    setSaveError(null);
    setConflict(null);
    setConfirmDiscard(false);
    setSelectionNotice(null);
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
    onDirtyChange?.(dirtyRef.current);
  }, [draft.dirtyTracks, onDirtyChange]);

  useEffect(
    () => () => onDirtyChangeRef.current?.(false),
    [],
  );

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
      void (async () => {
        await reload();
        setLoadedContextRefreshKey(refreshKey);
      })();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey, stopPreview]);

  // Space 键 → pan 模式（松开时结束）
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (
        e.code === "Space" &&
        !isEditableTarget(e.target) &&
        editorRootRef.current?.contains(globalThis.document.activeElement)
      ) {
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

  // 当前轨道 draft notes（未编辑则 fallback 到 document notes）
  const trackDraftNotes: MidiEditorNote[] = useMemo(() => {
    if (!selectedTrack) return [];
    const draftNotes = draft.draftNotesByTrack[selectedTrack.id];
    return draftNotes ?? selectedTrack.notes;
  }, [selectedTrack, draft.draftNotesByTrack]);

  const selectedNotes = useMemo(
    () => trackDraftNotes.filter((note) => selectedNoteIds.has(note.id)),
    [trackDraftNotes, selectedNoteIds],
  );
  const selectedNote = selectedNotes.length === 1 ? selectedNotes[0] : null;
  const selectedSummary = useMemo(() => summarizeSelectedNotes(selectedNotes), [selectedNotes]);

  useEffect(() => {
    const validIds = new Set(trackDraftNotes.map((note) => note.id));
    setSelectedNoteIds((current) => {
      const next = new Set(Array.from(current).filter((id) => validIds.has(id)));
      return next.size === current.size ? current : next;
    });
  }, [trackDraftNotes]);

  const pitchRange = useMemo(
    () => selectedTrack?.isDrum
      ? computeDrumPitchRange(trackDraftNotes)
      : trackDraftNotes.length
        ? computePitchRange(trackDraftNotes)
        : { minPitch: 48, maxPitch: 84 },
    [selectedTrack?.isDrum, trackDraftNotes],
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
  const musicContext = useMemo(
    () => document && musicSpec && document.songId === songId && loadedContextRefreshKey === refreshKey
      ? buildMidiEditorMusicContext(musicSpec, document.ppq, meter, document.totalBars)
      : null,
    [document, loadedContextRefreshKey, meter, musicSpec, refreshKey, songId],
  );
  const selectedTrackRole = selectedTrack
    ? musicContext?.trackRoles.get(selectedTrack.id) || selectedTrack.role
    : null;
  const overlapWarning = useMemo(
    () => bassOverlapWarning(selectedTrackRole, trackDraftNotes),
    [selectedTrackRole, trackDraftNotes],
  );
  const timelineMaxTick = Math.max(songMaxTick, musicContext?.totalTicks ?? 0);

  const handleVelocityCommit = (value: number) => {
    if (!selectedTrack || selectedNoteIds.size === 0 || isTrackLocked) return;
    const clamped = Math.max(1, Math.min(127, Math.round(value)));
    draft.setNotesVelocity(selectedTrack.id, selectedNoteIds, clamped);
  };

  const handleSelectNotes = useCallback((noteIds: string[], intent: SelectionIntent) => {
    setSelectedNoteIds((current) => applySelection(current, noteIds, intent));
    setSelectionNotice(null);
  }, []);

  const editorOwnsKeyboard = useCallback((event: KeyboardEvent) => {
    const root = editorRootRef.current;
    if (!root) return false;
    const target = event.target;
    return (
      editorActiveRef.current &&
      ((target instanceof Node && root.contains(target)) ||
        root.contains(globalThis.document.activeElement) ||
        target === window)
    );
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!selectedTrack || !editorOwnsKeyboard(event) || isEditableTarget(event.target)) return;
      const key = event.key.toLowerCase();
      const primary = event.ctrlKey || event.metaKey;

      if (primary && key === "a") {
        event.preventDefault();
        setSelectedNoteIds(new Set(trackDraftNotes.map((note) => note.id)));
        return;
      }
      if (key === "escape") {
        event.preventDefault();
        setSelectedNoteIds(new Set());
        return;
      }
      if (primary && key === "c") {
        event.preventDefault();
        const clipboard = createMidiClipboard(selectedNotes, selectedTrack.isDrum);
        if (clipboard) clipboardRef.current = clipboard;
        setSelectionNotice(clipboard ? `已复制 ${clipboard.notes.length} 个音符` : null);
        return;
      }
      if (primary && key === "v") {
        event.preventDefault();
        if (isTrackLocked) {
          setSelectionNotice("当前轨道已锁定，不能粘贴");
          return;
        }
        const clipboard = clipboardRef.current;
        if (!clipboard) {
          setSelectionNotice("内部 MIDI 剪贴板为空");
          return;
        }
        const targetKind = selectedTrack.isDrum ? "drum" : "pitched";
        if (clipboard.sourceKind !== targetKind) {
          setSelectionNotice("鼓组轨与有调轨之间不能直接粘贴音符");
          return;
        }
        const anchor = snapTick(playback.currentTick, snap, document?.ppq ?? 480);
        const ids = draft.insertNotes(
          selectedTrack.id,
          materializeClipboard(clipboard, anchor, selectedTrack.channel),
        );
        setSelectedNoteIds(new Set(ids));
        setSelectionNotice(`已在 playhead 粘贴 ${ids.length} 个音符`);
        return;
      }
      if (primary && key === "d") {
        event.preventDefault();
        if (isTrackLocked || selectedNotes.length === 0) {
          if (isTrackLocked) setSelectionNotice("当前轨道已锁定，不能复制音符");
          return;
        }
        const ids = draft.insertNotes(selectedTrack.id, duplicateNotes(selectedNotes, selectedTrack.channel));
        setSelectedNoteIds(new Set(ids));
        setSelectionNotice(`已复制 ${ids.length} 个音符`);
        return;
      }
      if (primary && key === "z") {
        event.preventDefault();
        if (event.shiftKey) draft.redo(selectedTrack.id);
        else draft.undo(selectedTrack.id);
        return;
      }
      if (primary && key === "y") {
        event.preventDefault();
        draft.redo(selectedTrack.id);
        return;
      }
      if ((key === "delete" || key === "backspace") && selectedNoteIds.size > 0) {
        event.preventDefault();
        if (isTrackLocked) {
          setSelectionNotice("当前轨道已锁定，不能删除音符");
          return;
        }
        draft.deleteNotes(selectedTrack.id, selectedNoteIds);
        setSelectedNoteIds(new Set());
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [
    document?.ppq,
    draft,
    editorOwnsKeyboard,
    isTrackLocked,
    playback.currentTick,
    selectedNoteIds,
    selectedNotes,
    selectedTrack,
    snap,
    trackDraftNotes,
  ]);

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
      if (!selectedTrackId || isTrackLocked) return;
      const id = draft.insertNotes(selectedTrackId, [note])[0];
      if (id) setSelectedNoteIds(new Set([id]));
    },
    [draft.insertNotes, isTrackLocked, selectedTrackId],
  );
  const handleMoveNotes = useCallback(
    (changes: Array<{ id: string; startTick: number; pitch: number }>) => {
      if (selectedTrackId && !isTrackLocked) draft.moveNotes(selectedTrackId, changes);
    },
    [draft.moveNotes, isTrackLocked, selectedTrackId],
  );
  const handleResizeNote = useCallback(
    (noteId: string, duration: number) => {
      if (selectedTrackId && !isTrackLocked) draft.resizeNote(selectedTrackId, noteId, duration);
    },
    [draft.resizeNote, isTrackLocked, selectedTrackId],
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
    setSelectedNoteIds(new Set());
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
      <div
        className="midi-editor"
        ref={editorRootRef}
        tabIndex={0}
        onPointerDownCapture={(event) => {
          editorActiveRef.current = true;
          if (!isEditableTarget(event.target)) editorRootRef.current?.focus({ preventScroll: true });
        }}
        onFocusCapture={() => {
          editorActiveRef.current = true;
        }}
        onBlurCapture={(event) => {
          if (!editorRootRef.current?.contains(event.relatedTarget as Node | null)) {
            editorActiveRef.current = false;
          }
        }}
      >
        <TrackSelector
          tracks={document.tracks}
          selectedTrackId={selectedTrack.id}
          onSelect={(trackId) => {
            setSelectedTrackId(trackId);
            setSelectedNoteIds(new Set());
            setSelectionNotice(null);
          }}
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

          {musicContext &&
            (Boolean(musicContext.scale && !selectedTrack.isDrum) ||
              musicContext.chords.length > 0 ||
              musicContext.sections.length > 0) && (
              <span className="midi-editor__semantic-controls" aria-label="Music context overlays">
                {musicContext.scale && !selectedTrack.isDrum && (
                  <button
                    type="button"
                    className="midi-editor__semantic-toggle"
                    aria-pressed={showScale}
                    onClick={() => setShowScale((value) => !value)}
                    title={`Scale: ${musicContext.scale.label}`}
                  >
                    Scale {showScale ? "✓" : ""}
                  </button>
                )}
                {musicContext.chords.length > 0 && (
                  <button
                    type="button"
                    className="midi-editor__semantic-toggle"
                    aria-pressed={showChords}
                    onClick={() => setShowChords((value) => !value)}
                  >
                    Chords {showChords ? "✓" : ""}
                  </button>
                )}
                {musicContext.sections.length > 0 && (
                  <button
                    type="button"
                    className="midi-editor__semantic-toggle"
                    aria-pressed={showSections}
                    onClick={() => setShowSections((value) => !value)}
                  >
                    Sections {showSections ? "✓" : ""}
                  </button>
                )}
              </span>
            )}

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
            Ctrl/Cmd+A 全选 · C/V 复制粘贴 · D 复制副本 · Shift/Ctrl 点击多选 · 空白拖动框选 · Delete 批量删除
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
                maxTick={Math.max(timelineMaxTick, 0)}
                pixelsPerTick={layout.pixelsPerTick}
                currentTick={playback.currentTick}
                loopEnabled={playback.loopEnabled}
                loopStartTick={playback.loopStartTick}
                loopEndTick={playback.loopEndTick}
                onSeek={playback.seek}
                sections={musicContext?.sections}
                chords={musicContext?.chords}
                showSections={showSections}
                showChords={showChords}
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
                isDrum={selectedTrack.isDrum}
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
                selectedNoteIds={selectedNoteIds}
                locked={isTrackLocked}
                panEnabled={spacePressed}
                onSelectNotes={handleSelectNotes}
                onAddNote={handleAddNote}
                onMoveNotes={handleMoveNotes}
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
                maxTimelineTick={timelineMaxTick}
                pitchRange={pitchRange}
                scale={showScale && !selectedTrack.isDrum ? musicContext?.scale : null}
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
          <span data-testid="selected-note-count">Selected: {selectedNoteIds.size}</span>
          {musicContext?.scale && !selectedTrack.isDrum && <span>Scale: {musicContext.scale.label}</span>}
          {selectedNote && (
            <span className="midi-editor__selected-note">
              {midiPitchToNoteName(selectedNote.pitch)} ({selectedNote.pitch}) · bar{" "}
              {tickToBar(selectedNote.startTick, document.ppq, meter)} · beat{" "}
              {tickToBeat(selectedNote.startTick, document.ppq).toFixed(2)}
            </span>
          )}
        </div>

        {selectedSummary && selectedTrack && (
          <div className="midi-editor__inspector">
            {selectedSummary.count > 1 && (
              <span className="midi-editor__selection-summary">
                {selectedSummary.count} notes · tick {selectedSummary.startTick}–{selectedSummary.endTick} · pitch{" "}
                {midiPitchToNoteName(selectedSummary.minPitch)}–{midiPitchToNoteName(selectedSummary.maxPitch)} · avg velocity{" "}
                {selectedSummary.averageVelocity}
              </span>
            )}
            <label className="midi-editor__velocity">
              {selectedSummary.count > 1 ? "Batch velocity" : "Velocity"}
              <input
                type="number"
                min={1}
                max={127}
                value={selectedNote?.velocity ?? selectedSummary.averageVelocity}
                disabled={isTrackLocked}
                onChange={(e) => {
                  const v = Number(e.target.value);
                  if (!Number.isNaN(v)) handleVelocityCommit(v);
                }}
                aria-label={selectedSummary.count > 1 ? "Batch velocity 力度" : "Velocity 力度"}
              />
            </label>
          </div>
        )}

        {selectionNotice && (
          <InlineNotice variant="warning" title="MIDI Selection">
            {selectionNotice}
          </InlineNotice>
        )}

        {overlapWarning && (
          <InlineNotice variant="warning" title="Bass overlap">
            {overlapWarning}
          </InlineNotice>
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
