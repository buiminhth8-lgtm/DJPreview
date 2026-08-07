// ProjectStatusBadges：工程卡片状态角标（T33.3）。
// 只显示 ProjectSummary 真实字段，不做额外请求。

import type { ProjectSummary } from "./projectTypes";
import { StatusBadge } from "../../components/ui";

export interface ProjectStatusBadgesProps {
  project: ProjectSummary;
}

export function ProjectStatusBadges({ project }: ProjectStatusBadgesProps) {
  return (
    <span className="project-card__badges">
      {project.hasMidi && <StatusBadge variant="info">MIDI</StatusBadge>}
      {project.hasAudio && <StatusBadge variant="success">WAV</StatusBadge>}
      {project.hasQualityReport && <StatusBadge variant="neutral">质量</StatusBadge>}
      {project.renderer === "fallback" && <StatusBadge variant="warning">Fallback</StatusBadge>}
      {project.renderer === "fluidsynth" && <StatusBadge variant="success">FluidSynth</StatusBadge>}
      {project.soundfontName && <StatusBadge variant="neutral">SF</StatusBadge>}
    </span>
  );
}
