// MusicSpecPanel：MusicSpec 预览（摘要 + JSON）。
// 始终显示；无 MusicSpec 时 Empty State；有数据时摘要 + 可滚动 JSON。

import type { MusicSpec } from "../../api/types";
import { EmptyState, KeyValueGrid, SectionCard } from "../../components/ui";
import { JsonPreview } from "../../shared/components/JsonPreview";

export interface MusicSpecPanelProps {
  musicSpec?: MusicSpec | null;
  requestId?: string | null;
}

const DASH = "—";

export function MusicSpecPanel({ musicSpec, requestId }: MusicSpecPanelProps) {
  if (!musicSpec) {
    return (
      <SectionCard title="MusicSpec" description="生成结果结构预览">
        <EmptyState
          title="暂无 MusicSpec"
          description="输入音乐描述并点击生成，或导入 .aimusic.zip 工程。"
        />
      </SectionCard>
    );
  }

  const key = musicSpec.tonality?.key ?? DASH;
  const mode = musicSpec.tonality?.mode ?? DASH;
  const meterNum = musicSpec.meter?.numerator;
  const meterDen = musicSpec.meter?.denominator;

  const summary = [
    { label: "标题", value: musicSpec.title || DASH },
    {
      label: "风格",
      value: musicSpec.style && musicSpec.style.length > 0 ? musicSpec.style.join(", ") : DASH,
    },
    {
      label: "情绪",
      value: musicSpec.mood && musicSpec.mood.length > 0 ? musicSpec.mood.join(", ") : DASH,
    },
    { label: "BPM", value: musicSpec.tempo?.bpm ?? DASH },
    { label: "调性", value: `${key} ${mode}`.trim() },
    { label: "拍号", value: meterNum && meterDen ? `${meterNum}/${meterDen}` : DASH },
    { label: "长度", value: musicSpec.length?.bars ? `${musicSpec.length.bars} 小节` : DASH },
    { label: "段落数", value: musicSpec.form?.length ?? DASH },
    { label: "轨道数", value: musicSpec.tracks?.length ?? DASH },
    { label: "request_id", value: requestId ? requestId.slice(0, 8) + "…" : DASH },
  ];

  return (
    <SectionCard title="MusicSpec" description="生成结果结构预览">
      <KeyValueGrid items={summary} columns={2} />
      <JsonPreview value={musicSpec} maxHeight={420} />
    </SectionCard>
  );
}
