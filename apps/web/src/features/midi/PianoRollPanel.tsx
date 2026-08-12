// PianoRollPanel：Piano Roll（常驻）。
// 无 MIDI / songId 时 Empty State（保留生成 MIDI 入口），绝不请求；
// 有 MIDI 时挂载新的只读 MIDI Editor（T34.3：轨道选择 + 音符查看）。

import { ActionButton, ButtonRow, EmptyState, SectionCard } from "../../components/ui";
import { MidiEditor } from "./editor/MidiEditor";
import type { MusicSpec } from "../../api/types";

export interface PianoRollPanelProps {
  songId?: string | null;
  hasMidi?: boolean;
  hasMusicSpec?: boolean;
  midiUrl?: string | null;
  isGeneratingMidi?: boolean;
  refreshKey?: number;
  editorSessionKey?: number;
  onGenerateMidi?: () => void;
  onMidiSaved?: (versionId: string) => void;
  onMidiDirtyChange?: (dirty: boolean) => void;
  onError?: (message: string) => void;
  musicSpec?: MusicSpec | null;
}

export function PianoRollPanel({
  songId,
  hasMidi = false,
  hasMusicSpec = false,
  isGeneratingMidi = false,
  refreshKey = 0,
  editorSessionKey = 0,
  onGenerateMidi,
  onMidiSaved,
  onMidiDirtyChange,
  musicSpec = null,
}: PianoRollPanelProps) {
  const canLoadRoll = Boolean(songId) && hasMidi;

  let body;
  if (!canLoadRoll) {
    body = (
      <EmptyState
        title="暂无 MIDI"
        description="生成 MIDI 后可查看音符分布。"
        action={
          onGenerateMidi ? (
            <ButtonRow>
              <ActionButton
                variant="secondary"
                onClick={onGenerateMidi}
                disabled={!hasMusicSpec || isGeneratingMidi}
                disabledReason={!hasMusicSpec ? "请先生成 MusicSpec" : undefined}
                loading={isGeneratingMidi}
              >
                {isGeneratingMidi ? "MIDI 生成中…" : "生成 MIDI"}
              </ActionButton>
            </ButtonRow>
          ) : undefined
        }
      />
    );
  } else {
    body = (
      <div className="workspace-piano-roll">
        <MidiEditor
          key={`${songId}:${editorSessionKey}`}
          songId={songId}
          refreshKey={refreshKey}
          onSaved={onMidiSaved}
          onDirtyChange={onMidiDirtyChange}
          musicSpec={musicSpec}
        />
      </div>
    );
  }

  return (
    <SectionCard
      title="Piano Roll"
      description="MIDI 音符分布"
      badge={hasMidi ? <span className="status-chip status-ok">MIDI ready</span> : undefined}
    >
      {body}
    </SectionCard>
  );
}
