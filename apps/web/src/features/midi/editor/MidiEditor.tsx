// features/midi/editor/MidiEditor.tsx（T34.3）
// MIDI Editor 顶层：组合 TrackSelector + TimelineHeader + PianoKeyboard + PianoRollViewport。
// 数据来自 useMidiEditorDocument(songId)（T34.1）；本阶段只读。
// songId 变化 → hook 重新加载；selectedTrackId 根据新 document 重新判定。

import { useEffect, useMemo, useState } from "react";
import { useMidiEditorDocument } from "./useMidiEditorDocument";
import { TrackSelector } from "./TrackSelector";
import { TimelineHeader } from "./TimelineHeader";
import { PianoKeyboard } from "./PianoKeyboard";
import { PianoRollViewport } from "./PianoRollViewport";
import type { MidiEditorDocument, MidiEditorNote, MidiEditorTrack } from "./midiEditorTypes";
import { computePitchRange, DEFAULT_LAYOUT, tickToBar, tickToBeat } from "./midiEditorLayout";
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
  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(null);
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);

  // songId 或 document 变化：重选有效轨道、清空 note 选择
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

  const selectedNote: MidiEditorNote | null = useMemo(() => {
    if (!selectedTrack) return null;
    return selectedTrack.notes.find((n) => n.id === selectedNoteId) ?? null;
  }, [selectedTrack, selectedNoteId]);

  const meter = { numerator: document?.timeSignature?.[0] ?? 4, denominator: document?.timeSignature?.[1] ?? 4 };

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
    const pitchRange = computePitchRange(selectedTrack.notes);
    const maxTick = selectedTrack.notes.length
      ? Math.max(...selectedTrack.notes.map((n) => n.startTick + n.durationTick))
      : 0;
    body = (
      <div className="midi-editor">
        <TrackSelector
          tracks={document.tracks}
          selectedTrackId={selectedTrack.id}
          onSelect={setSelectedTrackId}
        />

        <div className="midi-editor__board">
          <div className="midi-editor__timeline-row">
            <div className="midi-editor__timeline-spacer" style={{ width: DEFAULT_LAYOUT.keyboardWidth }} />
            <div className="midi-editor__timeline-scroll">
              <TimelineHeader
                ppq={document.ppq}
                meter={meter}
                maxTick={maxTick}
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
                notes={selectedTrack.notes}
                ppq={document.ppq}
                meter={meter}
                bpm={document.bpm}
                selectedNoteId={selectedNoteId}
                onSelectNote={setSelectedNoteId}
              />
            </div>
          </div>
        </div>

        <div className="midi-editor__footer">
          <span>Track: {selectedTrack.name}</span>
          <span>Notes: {selectedTrack.notes.length}</span>
          <span>PPQ: {document.ppq}</span>
          <span>Version: {document.versionId ?? "—"}</span>
          {selectedNote && (
            <span className="midi-editor__selected-note">
              Selected: pitch {selectedNote.pitch} · bar {tickToBar(selectedNote.startTick, document.ppq, meter)} ·
              beat {tickToBeat(selectedNote.startTick, document.ppq).toFixed(2)} · vel {selectedNote.velocity}
            </span>
          )}
        </div>
      </div>
    );
  }

  return (
    <SectionCard
      title="MIDI Editor"
      description="轨道选择与音符查看"
      badge={document ? <span className="status-chip status-ok">{document.tracks.length} tracks</span> : undefined}
    >
      {body}
    </SectionCard>
  );
}
