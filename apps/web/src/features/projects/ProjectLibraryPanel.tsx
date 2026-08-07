// ProjectLibraryPanel：工程库主体（T33.3）。
// 只接收数据与回调，不直接调用 backend。

import { useMemo, useState } from "react";
import type { ProjectSummary } from "./projectTypes";
import { ProjectCard } from "./ProjectCard";
import { ActionButton, ButtonRow, EmptyState } from "../../components/ui";

export type ProjectStatusFilter = "all" | "audio" | "midi" | "fallback";

export interface ProjectLibraryPanelProps {
  projects: ProjectSummary[];
  onDelete: (project: ProjectSummary) => void;
  onExport?: (project: ProjectSummary) => void;
  onRefresh: () => void;
  isRefreshing?: boolean;
}

const FILTER_OPTIONS: Array<{ value: ProjectStatusFilter; label: string }> = [
  { value: "all", label: "全部" },
  { value: "audio", label: "有 WAV" },
  { value: "midi", label: "有 MIDI" },
  { value: "fallback", label: "Fallback" },
];

function matchesFilter(project: ProjectSummary, filter: ProjectStatusFilter): boolean {
  switch (filter) {
    case "audio":
      return project.hasAudio;
    case "midi":
      return project.hasMidi;
    case "fallback":
      return project.renderer === "fallback";
    default:
      return true;
  }
}

export function ProjectLibraryPanel({
  projects,
  onDelete,
  onExport,
  onRefresh,
  isRefreshing = false,
}: ProjectLibraryPanelProps) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<ProjectStatusFilter>("all");

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    return projects.filter((p) => {
      if (!matchesFilter(p, filter)) return false;
      if (!q) return true;
      return (
        p.title.toLowerCase().includes(q) ||
        p.songId.toLowerCase().includes(q)
      );
    });
  }, [projects, search, filter]);

  return (
    <div className="project-library">
      <div className="project-library__toolbar">
        <input
          className="project-library__search"
          type="search"
          placeholder="搜索标题或 songId…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="搜索工程"
        />
        <select
          className="project-library__filter"
          value={filter}
          onChange={(e) => setFilter(e.target.value as ProjectStatusFilter)}
          aria-label="按状态筛选工程"
        >
          {FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <ActionButton variant="secondary" onClick={onRefresh} loading={isRefreshing} disabled={isRefreshing}>
          刷新
        </ActionButton>
      </div>

      {visible.length === 0 ? (
        search.trim() || filter !== "all" ? (
          <EmptyState
            title="没有符合当前条件的工程"
            description="尝试调整搜索词或筛选条件。"
            action={
              <ButtonRow>
                <ActionButton variant="secondary" onClick={() => setSearch("")}>
                  清除搜索
                </ActionButton>
                <ActionButton variant="ghost" onClick={() => setFilter("all")}>
                  清除筛选
                </ActionButton>
              </ButtonRow>
            }
          />
        ) : (
          <EmptyState
            title="暂无工程"
            description="输入一句话开始创建音乐，或导入已有 .aimusic.zip 工程。"
          />
        )
      ) : (
        <div className="project-library__grid">
          {visible.map((project) => (
            <ProjectCard
              key={project.songId}
              project={project}
              onDelete={onDelete}
              onExport={onExport}
            />
          ))}
        </div>
      )}
    </div>
  );
}
