// features/midi/editor/MidiEditor.tsx（T34.4）
// MIDI Editor：组合 TrackSelector + Snap 工具栏 + TimelineHeader + PianoKeyboard +
// PianoRollViewport（可编辑 draft）+ NoteInspector（velocity）。
// Draft 由 useMidiEditorDraft 管理；本阶段不调用 Save API。

import { useEffect, useMemo, useRef, useState } from "react";
import { useMidiEditorDocument } from "./useMidiEditorDocument";
import { useMidiEditorDraft } from "./useMidiEditorDraft";
import { useMidiViewport } from "./useMidiViewport";
import { TrackSelector } from "./TrackSelector";
import { TimelineHeader } from "./TimelineHeader";
import { PianoKeyboard } from "./PianoKeyboard";
import { PianoRollViewport } from "./PianoRollViewport";
import type { MidiEditorDocument, MidiEditorNote, MidiEditorTrack } from "./midiEditorTypes";
import { computePitchRange, DEFAULT_LAYOUT, tickToBar, tickToBeat } from "./midiEditorLayout";
import { DEFAULT_SNAP, SNAP_OPTIONS, midiPitchToNoteName, type SnapValue } from "./midiEditorGeometry";
import { documentMaxTick } from "./midiEditorGeometry";
import { EmptyState, ErrorState, LoadingState, SectionCard } from "../../../components/ui";

export interface MidiEditorProps {
  songId?: string | null;
  refreshKey?: number;
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

export function MidiEditor({ songId, refreshKey = 0 }: MidiEditorProps) {
  const { document, isLoading, error, notFound, reload } = useMidiEditorDocument(songId);
  const draft = useMidiEditorDraft(document);
  const viewport = useMidiViewport();
  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(null);
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [snap, setSnap] = useState<SnapValue>(DEFAULT_SNAP);
  const [lockedTrackIds, setLockedTrackIds] = useState<Set<string>>(new Set());
  const [spacePressed, setSpacePressed] = useState(false);

  // songId 或 document 变化：重选有效轨道、清空 note 选择（draft hook 已自行重置）
  useEffect(() => {
    setSelectedNoteId(null);
    setLockedTrackIds(new Set());
    viewport.resetZoom();
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

  // refreshKey 变化（MIDI 重新生成 / 版本恢复）→ 重新加载 document
  useEffect(() => {
    if (refreshKey > 0) {
      void reload();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

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

  const meter = { numerator: document?.timeSignature?.[0] ?? 4, denominator: document?.timeSignature?.[1] ?? 4 };
  const songMaxTick = document ? documentMaxTick(document.tracks) : 0;

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
    const pitchRange = trackDraftNotes.length
      ? computePitchRange(trackDraftNotes)
      : { minPitch: selectedTrack.channel === 9 ? 36 : 48, maxPitch: selectedTrack.channel === 9 ? 60 : 84 };
    const layout = {
      pixelsPerTick: viewport.pixelsPerTick,
      rowHeight: viewport.rowHeight,
      keyboardWidth: DEFAULT_LAYOUT.keyboardWidth,
    };
    body = (
      <div className="midi-editor">
        <TrackSelector
          tracks={document.tracks}
          selectedTrackId={selectedTrack.id}
          onSelect={setSelectedTrackId}
        />

        <div className="midi-editor__toolbar">
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

          <button type="button" className="ui-action-button ui-action-button--secondary" onClick={toggleTrackLock} aria-pressed={isTrackLocked}>
            {isTrackLocked ? "🔒 已锁定" : "🔓 编辑"}
          </button>

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
          <span className="midi-editor__toolbar-hint">
            Ctrl+滚轮缩放 · Shift+滚轮横滚 · Space+拖动平移 · 双击添加 · 右边缘拉长 · Delete 删除
          </span>
        </div>

        <div className="midi-editor__board" ref={viewportRef}>
          <div className="midi-editor__timeline-row">
            <div className="midi-editor__timeline-spacer" style={{ width: DEFAULT_LAYOUT.keyboardWidth }} />
            <div className="midi-editor__timeline-scroll">
              <TimelineHeader
                ppq={document.ppq}
                meter={meter}
                maxTick={Math.max(songMaxTick, 0)}
                pixelsPerTick={layout.pixelsPerTick}
              />
            </div>
          </div>
          <div className="midi-editor__roll-row">
            <div className="midi-editor__keyboard-scroll">
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
                onAddNote={(note) => {
                  draft.addNote(selectedTrack.id, note);
                }}
                onMoveNote={(noteId, start, pitch) => draft.moveNote(selectedTrack.id, noteId, start, pitch)}
                onResizeNote={(noteId, duration) => draft.resizeNote(selectedTrack.id, noteId, duration)}
                onZoomH={(dir) => (dir > 0 ? viewport.zoomHIn() : viewport.zoomHOut())}
                layout={layout}
              />
            </div>
          </div>
        </div>

        <div className="midi-editor__footer">
          <span>Track: {selectedTrack.name}</span>
          <span>Notes: {trackDraftNotes.length}</span>
          <span>PPQ: {document.ppq}</span>
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
