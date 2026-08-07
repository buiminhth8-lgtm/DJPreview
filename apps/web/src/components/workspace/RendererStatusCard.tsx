// RendererStatusCard：当前音频渲染器与音色质量状态（T39-A / T39-B）。
// 常驻展示 renderer / quality / SoundFont；仅当 is_fallback=true 时显示 fallback 提示，
// 并展示结构化 fallback_reason 与 FluidSynth 可用状态。

import type { AudioRenderMetadata, FallbackReason, RendererWarning } from "../../api/types";
import { EmptyState, InlineNotice, KeyValueGrid, SectionCard, StatusBadge } from "../ui";

export interface RendererStatusCardProps {
  metadata?: AudioRenderMetadata | null;
  compact?: boolean;
}

const QUALITY_LABEL: Record<string, string> = {
  preview: "预览级",
  basic: "基础",
  soundfont: "采样音源",
  unknown: "未知",
};

const FALLBACK_REASON_LABEL: Record<FallbackReason, string> = {
  no_soundfont_selected: "未选择 SoundFont",
  soundfont_file_missing: "SoundFont 文件缺失",
  soundfont_not_found: "SoundFont 未找到",
  fluidsynth_unavailable: "FluidSynth 不可用",
  fluidsynth_render_failed: "FluidSynth 渲染失败",
  renderer_not_configured: "渲染器未配置",
  unknown: "未知原因",
};

function warningSeverity(w: RendererWarning): "warning" | "info" {
  return w.code === "FALLBACK_RENDERER_QUALITY" ? "warning" : "info";
}

export function RendererStatusCard({ metadata, compact = false }: RendererStatusCardProps) {
  const renderer = metadata?.renderer ?? metadata?.rendererLabel ?? null;
  const quality = metadata?.quality ?? null;
  const soundfontName = metadata?.soundfontName ?? null;
  const rendererWarnings: RendererWarning[] = metadata?.warnings ?? [];
  const isFallback = metadata?.isFallback ?? (renderer === "fallback" || quality === "preview");
  const fallbackReason = metadata?.fallbackReason ?? null;

  const isSoundfont = quality === "soundfont" || Boolean(soundfontName);

  const items = [
    {
      label: "当前渲染器",
      value: isFallback ? "Fallback Preview Renderer" : renderer || "未知",
    },
    {
      label: "音色质量",
      value: quality ? QUALITY_LABEL[quality] ?? quality : "未知",
    },
    {
      label: "SoundFont",
      value: soundfontName ? soundfontName : "未使用",
    },
  ];

  return (
    <SectionCard title="渲染器状态" description="当前 WAV 使用的渲染器与音源" compact={compact}>
      <KeyValueGrid items={items} columns={3} />

      {isFallback ? (
        <InlineNotice variant="warning" title="当前为预览级音色（fallback）">
          当前使用简易 fallback renderer，音色为预览级合成，bass、drums、pad 可能不真实。
          {fallbackReason ? ` 原因：${FALLBACK_REASON_LABEL[fallbackReason] ?? fallbackReason}。` : ""}
          请选择 SoundFont（或安装 FluidSynth）并重新渲染 WAV，以获得更接近真实乐器或高质量合成器的音色。
        </InlineNotice>
      ) : isSoundfont ? (
        <InlineNotice variant="success" title="已使用采样音源">
          当前使用 FluidSynth + SoundFont 渲染：{soundfontName ?? "未命名音源"}，音色为采样音源。
        </InlineNotice>
      ) : (
        <EmptyState title="暂无渲染器信息" description="渲染 WAV 后将在这里显示当前使用的 renderer 和音源质量。" />
      )}

      {rendererWarnings.length > 0 && (
        <div className="renderer-status__warnings">
          {rendererWarnings.map((w, i) => (
            <InlineNotice key={i} variant={warningSeverity(w)}>
              {w.message || "未知警告"}
            </InlineNotice>
          ))}
        </div>
      )}

      <div className="renderer-status__badges">
        {quality && <StatusBadge variant={isFallback ? "warning" : isSoundfont ? "success" : "info"}>{`质量：${QUALITY_LABEL[quality] ?? quality}`}</StatusBadge>}
        {renderer && <StatusBadge variant="neutral">renderer={renderer}</StatusBadge>}
      </div>
    </SectionCard>
  );
}
