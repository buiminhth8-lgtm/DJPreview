// ProjectOverviewPanel：当前工程概览（T38-D）。
// 纯 props，不发请求；安全读取 musicSpec，字段缺失显示 —。
// 无工程时显示 Empty State。

import type { AudioRenderMetadata, MusicSpec } from "../../api/types";
import { EmptyState, KeyValueGrid, SectionCard, StatusBadge } from "../ui";

export interface ProjectOverviewPanelProps {
  songId?: string | null;
  currentVersionId?: string | null;
  musicSpec?: MusicSpec | null;
  warningCount?: number;
  hasMidi?: boolean;
  hasAudio?: boolean;
  lastRequestId?: string | null;
  audioRenderMetadata?: AudioRenderMetadata | null;
}

const DASH = "—";

const QUALITY_LABEL: Record<string, string> = {
  preview: "预览级",
  basic: "基础",
  soundfont: "采样音源",
  unknown: "未知",
};

export function ProjectOverviewPanel({
  songId,
  currentVersionId,
  musicSpec,
  warningCount = 0,
  hasMidi = false,
  hasAudio = false,
  lastRequestId,
  audioRenderMetadata = null,
}: ProjectOverviewPanelProps) {
  if (!musicSpec) {
    return (
      <SectionCard title="当前工程概览" description="生成或导入工程后显示摘要">
        <EmptyState
          title="尚未生成工程"
          description="输入音乐描述后点击生成 MusicSpec，或导入 .aimusic.zip 工程。"
        />
      </SectionCard>
    );
  }

  const key = musicSpec.tonality?.key ?? DASH;
  const mode = musicSpec.tonality?.mode ?? DASH;
  const meterNum = musicSpec.meter?.numerator;
  const meterDen = musicSpec.meter?.denominator;

  const rendererName = audioRenderMetadata?.rendererLabel ?? audioRenderMetadata?.renderer ?? null;
  const quality = audioRenderMetadata?.quality ?? null;
  const soundfontName = audioRenderMetadata?.soundfontName ?? null;
  const hasRendererMeta = Boolean(rendererName || quality || soundfontName);

  const items = [
    { label: "标题", value: musicSpec.title || DASH },
    {
      label: "风格",
      value: musicSpec.style && musicSpec.style.length > 0 ? musicSpec.style.join(", ") : DASH,
    },
    { label: "BPM", value: musicSpec.tempo?.bpm ?? DASH },
    { label: "调性", value: `${key} ${mode}`.trim() },
    { label: "拍号", value: meterNum && meterDen ? `${meterNum}/${meterDen}` : DASH },
    { label: "长度", value: musicSpec.length?.bars ? `${musicSpec.length.bars} 小节` : DASH },
    { label: "段落数", value: musicSpec.form?.length ?? DASH },
    { label: "轨道数", value: musicSpec.tracks?.length ?? DASH },
    {
      label: "Warnings",
      value: warningCount > 0 ? `${warningCount} 条` : "0 条",
    },
    { label: "song_id", value: songId ? `${songId.slice(0, 8)}…` : DASH },
    { label: "当前版本", value: currentVersionId ?? DASH },
    {
      label: "MIDI",
      value: hasMidi ? "ready" : "No MIDI",
    },
    {
      label: "WAV",
      value: hasAudio ? "ready" : "No Audio",
    },
    { label: "最近 request_id", value: lastRequestId ? lastRequestId.slice(0, 8) + "…" : DASH },
    ...(hasRendererMeta
      ? [
          { label: "Renderer", value: rendererName ?? DASH },
          { label: "Quality", value: quality ? (QUALITY_LABEL[quality] ?? quality) : DASH },
          { label: "SoundFont", value: soundfontName ? soundfontName : "none" },
        ]
      : []),
  ];

  const assetBadge = hasAudio ? (
    <StatusBadge variant="success">WAV ready</StatusBadge>
  ) : hasMidi ? (
    <StatusBadge variant="info">MIDI ready</StatusBadge>
  ) : (
    <StatusBadge variant="neutral">No assets</StatusBadge>
  );

  return (
    <SectionCard
      title="当前工程概览"
      description={songId ? `song_id：${songId.slice(0, 8)}…` : "工程摘要"}
      badge={warningCount > 0 ? <StatusBadge variant="warning">{warningCount} warnings</StatusBadge> : assetBadge}
    >
      <KeyValueGrid items={items} columns={2} />
    </SectionCard>
  );
}
