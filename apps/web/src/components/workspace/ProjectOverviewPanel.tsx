// ProjectOverviewPanel：当前工程轻量概览（纯 props，不发请求）。
// 有 musicSpec 时显示标题/风格/BPM/调性/拍号/长度/段落数/轨道数/warnings 数。

import type { MusicSpec } from "../../api/types";
import { EmptyState, KeyValueGrid, SectionCard, StatusBadge } from "../ui";

export interface ProjectOverviewPanelProps {
  songId?: string | null;
  musicSpec?: MusicSpec | null;
  warningCount?: number;
}

export function ProjectOverviewPanel({ songId, musicSpec, warningCount = 0 }: ProjectOverviewPanelProps) {
  if (!musicSpec) {
    return (
      <SectionCard title="当前工程概览" description="生成或导入工程后显示摘要">
        <EmptyState
          title="尚未生成工程"
          description="输入描述后点击生成 MusicSpec，或导入 .aimusic.zip 工程。"
        />
      </SectionCard>
    );
  }

  const items = [
    { label: "标题", value: musicSpec.title },
    { label: "风格", value: musicSpec.style.length > 0 ? musicSpec.style.join(", ") : "—" },
    { label: "BPM", value: musicSpec.tempo?.bpm },
    { label: "调性", value: musicSpec.tonality ? `${musicSpec.tonality.key} ${musicSpec.tonality.mode}` : "—" },
    { label: "拍号", value: musicSpec.meter ? `${musicSpec.meter.numerator}/${musicSpec.meter.denominator}` : "—" },
    { label: "长度", value: musicSpec.length ? `${musicSpec.length.bars} 小节` : "—" },
    { label: "段落数", value: musicSpec.form?.length ?? 0 },
    { label: "轨道数", value: musicSpec.tracks?.length ?? 0 },
  ];

  return (
    <SectionCard
      title="当前工程概览"
      description={songId ? `song_id：${songId.slice(0, 8)}…` : "工程摘要"}
      badge={
        warningCount > 0 ? (
          <StatusBadge variant="warning">{warningCount} warnings</StatusBadge>
        ) : (
          <StatusBadge variant="success">valid</StatusBadge>
        )
      }
    >
      <KeyValueGrid items={items} columns={2} />
    </SectionCard>
  );
}
