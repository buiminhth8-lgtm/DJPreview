// PlaybackDownloadPanel：播放与下载（常驻）。
// 无资产时 Empty State；有 WAV 时播放器；下载按钮无资产时 disabled 并显示原因。
// 不直接发无效请求；songId 为空时不生成 URL。

import type { AudioRenderMetadata } from "../../api/types";
import { ActionButton, ButtonRow, EmptyState, InlineNotice, SectionCard, StatusBadge } from "../../components/ui";
import { RendererStatusCard } from "./RendererStatusCard";

export interface PlaybackDownloadPanelProps {
  songId?: string | null;
  midiUrl?: string | null;
  wavUrl?: string | null;
  hasMidi?: boolean;
  hasAudio?: boolean;
  isRenderingAudio?: boolean;
  isGeneratingMidi?: boolean;
  hasMusicSpec?: boolean;
  audioRenderMetadata?: AudioRenderMetadata | null;
  audioNeedsRender?: boolean;
  selectedSoundfontName?: string | null;
  onGenerateMidi?: () => void;
  onRenderAudio?: () => void;
  onDownloadMidi?: () => void;
  onDownloadWav?: () => void;
}

export function PlaybackDownloadPanel({
  songId,
  midiUrl,
  wavUrl,
  hasMidi = false,
  hasAudio = false,
  isRenderingAudio = false,
  isGeneratingMidi = false,
  hasMusicSpec = false,
  audioRenderMetadata = null,
  audioNeedsRender = false,
  selectedSoundfontName = null,
  onGenerateMidi,
  onRenderAudio,
  onDownloadMidi,
  onDownloadWav,
}: PlaybackDownloadPanelProps) {
  const noSong = !songId;
  const hasWavUrl = Boolean(wavUrl);

  let body;
  if (!hasMusicSpec) {
    body = (
      <EmptyState
        title="暂无可播放音频"
        description="生成 MIDI 后可渲染 WAV，渲染完成后可播放和下载。"
      />
    );
  } else if (!hasMidi) {
    body = (
      <EmptyState title="MIDI 尚未生成" description="点击“生成 MIDI”开始；生成后可继续渲染 WAV 试听。" />
    );
  } else if (!hasAudio) {
    body = (
      <EmptyState
        title="MIDI 已生成"
        description="可以下载 MIDI，或继续渲染 WAV 以试听音频。"
      />
    );
  } else {
    body = hasWavUrl ? (
      <div className="workspace-playback">
        <audio className="workspace-playback__audio" controls preload="metadata" src={wavUrl ?? undefined} />
        {audioNeedsRender ? (
          <InlineNotice variant="warning" title="当前 WAV 需要重新渲染">
            {selectedSoundfontName
              ? `已选择新的 SoundFont：${selectedSoundfontName}。重新渲染后才会应用新音色。`
              : "工程配置（MIDI / 版本 / 音源）已变化。请重新渲染 WAV 以更新试听。"}
          </InlineNotice>
        ) : (
          <InlineNotice variant="success" title="音频已渲染">
            可以播放试听或下载 WAV。
          </InlineNotice>
        )}
        {audioRenderMetadata ? (
          <RendererStatusCard metadata={audioRenderMetadata} compact />
        ) : (
          <EmptyState title="暂无渲染器信息" description="渲染 WAV 后将在这里显示当前使用的 renderer 和音源质量。" />
        )}
      </div>
    ) : (
      <EmptyState title="音频已渲染" description="WAV 地址暂不可用，请尝试重新渲染。" />
    );
  }

  return (
    <SectionCard
      title="播放与下载"
      description="MIDI / WAV 试听与下载"
      badge={
        hasAudio ? (
          <StatusBadge variant="success">WAV ready</StatusBadge>
        ) : hasMidi ? (
          <StatusBadge variant="info">MIDI ready</StatusBadge>
        ) : (
          <StatusBadge variant="neutral">No assets</StatusBadge>
        )
      }
    >
      <ButtonRow className="workspace-asset-actions">
        {onGenerateMidi && (
          <ActionButton
            variant="secondary"
            onClick={onGenerateMidi}
            disabled={noSong || !hasMusicSpec || isGeneratingMidi}
            disabledReason={!hasMusicSpec ? "请先生成 MusicSpec" : noSong ? "请先生成 MusicSpec" : undefined}
            loading={isGeneratingMidi}
          >
            {isGeneratingMidi ? "MIDI 生成中…" : "生成 MIDI"}
          </ActionButton>
        )}
        {onRenderAudio && (
          <ActionButton
            variant="secondary"
            onClick={onRenderAudio}
            disabled={!hasMidi || isRenderingAudio}
            disabledReason={!hasMidi ? "请先生成 MIDI" : undefined}
            loading={isRenderingAudio}
          >
            {isRenderingAudio ? "WAV 渲染中…" : "渲染 WAV"}
          </ActionButton>
        )}
        {onDownloadMidi && (
          <ActionButton
            variant="ghost"
            onClick={onDownloadMidi}
            disabled={!hasMidi || !midiUrl}
            disabledReason={!hasMidi ? "当前工程暂无 MIDI" : undefined}
          >
            下载 MIDI
          </ActionButton>
        )}
        {onDownloadWav && (
          <ActionButton
            variant="ghost"
            onClick={onDownloadWav}
            disabled={!hasAudio || !hasWavUrl}
            disabledReason={!hasAudio ? "当前工程暂无音频" : undefined}
          >
            下载 WAV
          </ActionButton>
        )}
      </ButtonRow>
      {body}
    </SectionCard>
  );
}
