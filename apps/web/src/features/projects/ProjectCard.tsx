// ProjectCard：工程卡片（T33.3）。
// 展示真实 ProjectSummary 字段；点击打开工程；提供删除入口。
// 不做 N+1 请求：只使用传入的 project 数据。

import { useNavigate } from "react-router-dom";
import type { ProjectSummary } from "./projectTypes";
import { ProjectStatusBadges } from "./ProjectStatusBadges";
import { ActionButton, ButtonRow } from "../../components/ui";
import { formatDateTime } from "../../shared/utils/date";

export interface ProjectCardProps {
  project: ProjectSummary;
  onDelete: (project: ProjectSummary) => void;
  onExport?: (project: ProjectSummary) => void;
  selected?: boolean;
  onToggleSelect?: (songId: string) => void;
}

export function ProjectCard({
  project,
  onDelete,
  onExport,
  selected = false,
  onToggleSelect,
}: ProjectCardProps) {
  const navigate = useNavigate();
  const open = () => {
    navigate(`/projects/${encodeURIComponent(project.songId)}`);
  };

  return (
    <article
      className={`project-card${selected ? " project-card--selected" : ""}`}
      data-song-id={project.songId}
    >
      {onToggleSelect && (
        <label className="project-card__checkbox">
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onToggleSelect(project.songId)}
            onClick={(e) => e.stopPropagation()}
            aria-label={`选择工程 ${project.title}`}
          />
          <span>选择</span>
        </label>
      )}
      <button type="button" className="project-card__open" onClick={open} aria-label={`打开工程 ${project.title}`}>
        <span className="project-card__title">{project.title || "未命名工程"}</span>
        <span className="project-card__meta">
          {formatDateTime(project.createdAt)}
          {project.currentVersionId ? ` · ${project.currentVersionId}` : ""}
        </span>
        <span className="project-card__song-id">{project.songId.slice(0, 8)}…</span>
        <ProjectStatusBadges project={project} />
      </button>

      <ButtonRow className="project-card__actions">
        <ActionButton variant="secondary" onClick={open}>
          打开工程
        </ActionButton>
        {onExport && (
          <ActionButton variant="ghost" onClick={() => onExport(project)}>
            导出
          </ActionButton>
        )}
        <ActionButton
          variant="danger"
          onClick={() => onDelete(project)}
          aria-label={`删除工程 ${project.title}`}
        >
          删除
        </ActionButton>
      </ButtonRow>
    </article>
  );
}
