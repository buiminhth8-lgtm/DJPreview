// HarmonyProgressionView：和弦进行视图（按 section 分组，chord chips）。
// 支持空 progression、长进行换行、section 级 warning。

import { InlineNotice } from "../ui";

export interface HarmonyLike {
  section?: string;
  progression?: string[];
}

export interface HarmonyProgressionViewProps {
  harmony?: HarmonyLike[];
  sectionWarnings?: Record<string, unknown[]>;
}

export function HarmonyProgressionView({ harmony, sectionWarnings }: HarmonyProgressionViewProps) {
  const list = Array.isArray(harmony) ? harmony : [];
  return (
    <div className="workspace-harmony-progression">
      {list.length === 0 && (
        <div className="muted-note">暂无和弦进行。</div>
      )}
      {list.map((h, i) => {
        const section = h.section ?? `section-${i}`;
        const progression = Array.isArray(h.progression) ? h.progression : [];
        const warnings = sectionWarnings?.[section] ?? [];
        return (
          <div className="workspace-harmony-progression__section" key={`${section}-${i}`}>
            <div className="workspace-harmony-progression__head">
              <span className="workspace-harmony-progression__section-name">{section}</span>
              {warnings.length > 0 && (
                <span className="workspace-harmony-progression__warning-count">{warnings.length} warnings</span>
              )}
            </div>
            {progression.length === 0 ? (
              <div className="muted-note">（空进行）</div>
            ) : (
              <div className="workspace-harmony-progression__chords">
                {progression.map((chord, ci) => (
                  <span className="workspace-chord-chip" key={`${chord}-${ci}`}>
                    {chord}
                  </span>
                ))}
              </div>
            )}
            {warnings.length > 0 && (
              <div className="workspace-harmony-progression__warnings">
                {warnings.map((w, wi) => (
                  <InlineNotice key={wi} variant="warning">
                    {typeof w === "string" ? w : (w as { message?: string }).message || "校验警告"}
                  </InlineNotice>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
