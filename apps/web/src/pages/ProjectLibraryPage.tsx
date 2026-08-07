// ProjectLibraryPage：/projects 工程库页（T33.2 最小列表）。
// 复用 useProjects()；仅基础列表 + 进入工作台。搜索/筛选/删除确认/导入留 T33.3/T33.8。

import { Link } from "react-router-dom";
import { useProjects } from "../features/projects/useProjects";
import { EmptyState, LoadingState, SectionCard, StatusBadge } from "../components/ui";

export default function ProjectLibraryPage() {
  const { projects, isLoading, error, reload } = useProjects();

  let body;
  if (isLoading && projects.length === 0) {
    body = <LoadingState title="加载工程列表中…" />;
  } else if (error && projects.length === 0) {
    body = (
      <EmptyState
        title="工程列表加载失败"
        description={error}
        action={<button onClick={() => void reload()}>重试</button>}
      />
    );
  } else if (projects.length === 0) {
    body = (
      <EmptyState
        title="暂无工程"
        description="还没有工程。去创作页生成第一首歌吧。"
        action={
          <Link to="/create" className="ui-action-button ui-action-button--primary">
            去创作新音乐
          </Link>
        }
      />
    );
  } else {
    body = (
      <div className="project-library">
        <div className="project-library__toolbar">
          <button className="ui-action-button ui-action-button--secondary" onClick={() => void reload()}>
            刷新
          </button>
        </div>
        <ul className="project-library__list">
          {projects.map((project) => (
            <li key={project.songId} className="project-library__item">
              <Link to={`/projects/${project.songId}`} className="project-library__link">
                <span className="project-library__title">{project.title || "未命名工程"}</span>
                <span className="project-library__meta">
                  {project.createdAt ? new Date(project.createdAt).toLocaleDateString() : ""}
                  {project.currentVersionId ? ` · ${project.currentVersionId}` : ""}
                  {project.soundfontName ? ` · SF:${project.soundfontName}` : ""}
                </span>
                <span className="project-library__badges">
                  {project.hasAudio && <StatusBadge variant="success">WAV</StatusBadge>}
                  {project.hasMidi && <StatusBadge variant="info">MIDI</StatusBadge>}
                  {project.hasQualityReport && <StatusBadge variant="neutral">质量</StatusBadge>}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <div className="page page--projects">
      <SectionCard title="工程库" description="历史工程列表">
        {body}
      </SectionCard>
    </div>
  );
}
