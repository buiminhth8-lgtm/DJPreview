// SectionTimeline：曲式段落时间线（workspace 版，安全读取 unknown）。
// 展示 section id / name / start_bar / bars / energy。

export interface SectionLike {
  id?: string;
  name?: string;
  start_bar?: number;
  bars?: number;
  energy?: number;
}

export interface SectionTimelineProps {
  sections?: SectionLike[];
}

export function SectionTimeline({ sections }: SectionTimelineProps) {
  const list = Array.isArray(sections) ? sections : [];
  return (
    <div className="workspace-section-timeline">
      {list.map((s, i) => {
        const start = typeof s.start_bar === "number" ? s.start_bar : null;
        const bars = typeof s.bars === "number" ? s.bars : null;
        const end = start !== null && bars !== null ? start + bars - 1 : null;
        const energy = typeof s.energy === "number" ? s.energy : null;
        const pct = energy !== null ? Math.round(energy * 100) : null;
        return (
          <div className="workspace-section-timeline__card" key={s.id ?? `section-${i}`}>
            <div className="workspace-section-timeline__head">
              <span className="workspace-section-timeline__name">{s.name || "—"}</span>
              <span className="workspace-section-timeline__id">{s.id || "—"}</span>
            </div>
            <div className="workspace-section-timeline__detail">
              {end !== null ? `${start}–${end} 小节` : start !== null ? `从第 ${start} 小节` : "—"}
              {bars !== null ? ` · ${bars} bars` : ""}
            </div>
            <div className="workspace-section-timeline__energy">
              <span className="workspace-section-timeline__energy-label">energy</span>
              <span className="workspace-section-timeline__energy-bar">
                <span
                  className="workspace-section-timeline__energy-fill"
                  style={{ width: `${pct ?? 0}%` }}
                />
              </span>
              <span className="workspace-section-timeline__energy-value">{energy !== null ? energy.toFixed(2) : "—"}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
