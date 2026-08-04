import type { SectionSpec } from "../api/musicApi";

interface SectionTimelineProps {
  sections: SectionSpec[];
}

export default function SectionTimeline({ sections }: SectionTimelineProps) {
  return (
    <div className="section-timeline">
      {sections.map((section) => (
        <div className="section-card" key={section.id}>
          <div className="section-name">{section.name}</div>
          <div className="section-id">{section.id}</div>
          <div className="section-detail">
            第 {section.start_bar}-{section.start_bar + section.bars - 1} 小节
          </div>
          <div className="section-detail">{section.bars} bars</div>
          <div className="energy-row">
            <span>energy</span>
            <span className="energy-bar">
              <span
                className="energy-fill"
                style={{ width: `${Math.round(section.energy * 100)}%` }}
              />
            </span>
            <span>{section.energy.toFixed(2)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
