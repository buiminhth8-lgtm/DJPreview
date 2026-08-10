// features/midi/editor/MidiEditor.tsx（T34.4）
// MIDI Editor：组合 TrackSelector + Snap 工具栏 + TimelineHeader + PianoKeyboard +
// PianoRollViewport（可编辑 draft）+ NoteInspector（velocity）。
// Draft 由 useMidiEditorDraft 管理；本阶段不调用 Save API。

import { useEffect, useMemo, useState } from "react";
import { useMidiEditorDocument } from "./useMidiEditorDocument";
import { useMidiEditorDraft } from "./useMidiEditorDraft";
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

export function MidiEditor({ songId, refreshKey = 0 }: MidiEditorProps) {
  const { document, isLoading, error, notFound, reload } = useMidiEditorDocument(songId);
  const draft = useMidiEditorDraft(document);
  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(null);
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [snap, setSnap] = useState<SnapValue>(DEFAULT_SNAP);

  // songId 或 document 变化：重选有效轨道、清空 note 选择（draft hook 已自行重置）
  useEffect(() => {
    setSelectedNoteId(null);
    if (!document) {
      setSelectedTrackId(null);
      return;
    }
    setSelectedTrackId((prev) => {
      if (prev && document.tracks.some((t) => t.id === prev)) return prev;
      return defaultTrackId(document);
    });
  }, [document]);

  // refreshKey 变化（MIDI 重新生成 / 版本恢复）→ 重新加载 document
  useEffect(() => {
    if (refreshKey > 0) {
      void reload();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

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

  const meter = { numerator: document?.timeSignature?.[0] ?? 4, denominator: document?.timeSignature?.[1] ?? 4 };
  const songMaxTick = document ? documentMaxTick(document.tracks) : 0;

  // 删除选中 Note（Delete/Backspace，非输入框内）
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!selectedTrack || !selectedNoteId) return;
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT" || target.isContentEditable)) {
        return;
      }
      if (e.key === "Delete" || e.key === "Backspace") {
        e.preventDefault();
        draft.deleteNote(selectedTrack.id, selectedNoteId);
        setSelectedNoteId(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedTrack, selectedNoteId, draft]);

  const handleVelocityCommit = (value: number) => {
    if (!selectedTrack || !selectedNoteId) return;
    const clamped = Math.max(1, Math.min(127, Math.round(value)));
    draft.setVelocity(selectedTrack.id, selectedNoteId, clamped);
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
    const pitchRange = trackDraftNotes.length
      ? computePitchRange(trackDraftNotes)
      : { minPitch: selectedTrack.channel === 9 ? 36 : 48, maxPitch: selectedTrack.channel === 9 ? 60 : 84 };
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
          {isDirty && <span className="status-chip status-warning">未保存草稿</span>}
          <span className="midi-editor__toolbar-hint">双击空白添加 · 拖动移动 · 右边缘拉长 · Delete 删除</span>
        </div>

        <div className="midi-editor__board">
          <div className="midi-editor__timeline-row">
            <div className="midi-editor__timeline-spacer" style={{ width: DEFAULT_LAYOUT.keyboardWidth }} />
            <div className="midi-editor__timeline-scroll">
              <TimelineHeader
                ppq={document.ppq}
                meter={meter}
                maxTick={Math.max(songMaxTick, 0)}
                pixelsPerTick={DEFAULT_LAYOUT.pixelsPerTick}
              />
            </div>
          </div>
          <div className="midi-editor__roll-row">
            <div className="midi-editor__keyboard-scroll">
              <PianoKeyboard
                minPitch={pitchRange.minPitch}
                maxPitch={pitchRange.maxPitch}
                rowHeight={DEFAULT_LAYOUT.rowHeight}
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
                onSelectNote={setSelectedNoteId}
                onAddNote={(note) => {
                  draft.addNote(selectedTrack.id, note);
                }}
                onMoveNote={(noteId, start, pitch) => draft.moveNote(selectedTrack.id, noteId, start, pitch)}
                onResizeNote={(noteId, duration) => draft.resizeNote(selectedTrack.id, noteId, duration)}
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
