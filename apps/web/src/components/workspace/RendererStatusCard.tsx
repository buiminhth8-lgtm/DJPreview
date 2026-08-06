// RendererStatusCard：当前音频渲染器与音色质量状态（T39-A）。
// 常驻展示 renderer / quality / SoundFont；fallback 时给出预览级音色提示。
// 纯 props，不发请求；metadata 缺失时显示 Empty State。

import type { AudioRenderMetadata, RendererWarning } from "../../api/types";
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

function warningSeverity(w: RendererWarning): "warning" | "info" {
  return w.code === "FALLBACK_RENDERER_QUALITY" ? "warning" : "info";
}

export function RendererStatusCard({ metadata, compact = false }: RendererStatusCardProps) {
  const renderer = metadata?.renderer ?? metadata?.rendererLabel ?? null;
  const quality = metadata?.quality ?? null;
  const soundfontName = metadata?.soundfontName ?? null;
  const rendererWarnings: RendererWarning[] = metadata?.warnings ?? [];

  const fallbackWarning = rendererWarnings.find(
    (w) => w.code === "FALLBACK_RENDERER_QUALITY" || /fallback/i.test(w.message ?? ""),
  );
  const isFallback = renderer === "fallback" || quality === "preview" || Boolean(fallbackWarning);
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
        <InlineNotice variant="warning" title="当前为预览级音色">
          当前使用简易 fallback renderer，音色为预览级合成，bass、drums、pad 可能不真实。请选择 SoundFont
          并重新渲染 WAV，以获得更接近真实乐器或高质量合成器的音色。
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
