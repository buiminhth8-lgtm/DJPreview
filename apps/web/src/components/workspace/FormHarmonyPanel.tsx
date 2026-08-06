// FormHarmonyPanel：曲式与和声（常驻）。
// 无 MusicSpec 时 Empty State；有数据时显示 form timeline + harmony progression + section warnings。

import type { MusicSpec } from "../../api/types";
import { EmptyState, SectionCard } from "../ui";
import { HarmonyProgressionView, type HarmonyLike } from "./HarmonyProgressionView";
import { SectionTimeline, type SectionLike } from "./SectionTimeline";

export interface FormHarmonyPanelProps {
  musicSpec?: MusicSpec | null;
  warnings?: unknown[] | null;
}

const DASH = "—";

function sectionWarningsBySection(warnings: unknown[]): Record<string, unknown[]> {
  const result: Record<string, unknown[]> = {};
  for (const w of warnings ?? []) {
    if (typeof w === "string") {
      // 字符串 warning 无法可靠映射到 section，跳过
      continue;
    }
    if (typeof w !== "object" || w === null) continue;
    const rec = w as Record<string, unknown>;
    const section = rec.section ?? rec.section_id;
    if (typeof section === "string") {
      result[section] = result[section] ?? [];
      result[section].push(w);
    }
  }
  return result;
}

export function FormHarmonyPanel({ musicSpec, warnings }: FormHarmonyPanelProps) {
  if (!musicSpec) {
    return (
      <SectionCard title="曲式与和声" description="段落、起止小节和和弦进行">
        <EmptyState
          title="暂无曲式与和声"
          description="生成 MusicSpec 后将在这里显示段落、起止小节和和弦进行。"
        />
      </SectionCard>
    );
  }

  const sections: SectionLike[] = (musicSpec.form ?? []).map((s) => ({
    id: s.id,
    name: s.name,
    start_bar: s.start_bar,
    bars: s.bars,
    energy: s.energy,
  }));

  const harmony: HarmonyLike[] = (musicSpec.harmony ?? []).map((h) => ({
    section: h.section,
    progression: h.progression ?? [],
  }));

  const sectionWarnings = sectionWarningsBySection(warnings ?? []);

  // 找不到对应 form section 的和声提示
  const knownSections = new Set((musicSpec.form ?? []).map((s) => s.id));
  const orphanHarmony = harmony.filter((h) => h.section && !knownSections.has(h.section));

  return (
    <SectionCard title="曲式与和声" description="段落、起止小节和和弦进行">
      {sections.length === 0 ? (
        <EmptyState
          title="暂无曲式段落"
          description="生成 MusicSpec 后将在这里显示段落、起止小节和和弦进行。"
        />
      ) : (
        <>
          <SectionTimeline sections={sections} />
          {harmony.length > 0 && <HarmonyProgressionView harmony={harmony} sectionWarnings={sectionWarnings} />}
          {orphanHarmony.length > 0 && (
            <div className="workspace-form-harmony__orphan">
              <div className="muted-note">
                警告：{orphanHarmony.map((h) => h.section).join("、")} 的和声引用了不存在的段落。
              </div>
            </div>
          )}
        </>
      )}
    </SectionCard>
  );
}

export { DASH };
