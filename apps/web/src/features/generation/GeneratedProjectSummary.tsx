// features/generation/GeneratedProjectSummary.tsx（T33.4）
// 生成结果摘要：标题/songId/BPM/调性/拍号/风格/段落/轨道/warnings。
// 只展示真实 MusicSpec 字段；完整编辑进入工作台。

import { Link } from "react-router-dom";
import type { GeneratedProjectSummary as Summary } from "./generationTypes";
import { InlineNotice, KeyValueGrid, SectionCard } from "../../components/ui";

export interface GeneratedProjectSummaryProps {
  summary: Summary;
}

export function GeneratedProjectSummary({ summary }: GeneratedProjectSummaryProps) {
  const spec = summary.musicSpec;
  const items = [
    { label: "标题", value: summary.title || "未命名工程" },
    { label: "风格", value: spec.style?.length ? spec.style.join(", ") : "—" },
    { label: "BPM", value: spec.tempo?.bpm ?? "—" },
    { label: "调性", value: `${spec.tonality?.key ?? "—"} ${spec.tonality?.mode ?? ""}`.trim() },
    {
      label: "拍号",
      value: spec.meter?.numerator && spec.meter?.denominator ? `${spec.meter.numerator}/${spec.meter.denominator}` : "—",
    },
    { label: "段落数", value: spec.form?.length ?? "—" },
    { label: "轨道数", value: spec.tracks?.length ?? "—" },
    { label: "song_id", value: `${summary.songId.slice(0, 8)}…` },
  ];

  return (
    <SectionCard title="生成完成" description="新工程已创建">
      <KeyValueGrid items={items} columns={2} />

      {summary.warnings.length > 0 && (
        <InlineNotice variant="warning" title={`${summary.warnings.length} 个生成质量提示`}>
          {summary.warnings.map((w) => w.message).join("；")}
        </InlineNotice>
      )}

      <div className="generate-result__actions">
        <Link
          to={`/projects/${encodeURIComponent(summary.songId)}`}
          className="ui-action-button ui-action-button--primary"
        >
          进入工程工作台
        </Link>
        <span className="generate-result__hint">在工程工作台中可以继续生成 MIDI / WAV、编辑与导出。</span>
      </div>
    </SectionCard>
  );
}
