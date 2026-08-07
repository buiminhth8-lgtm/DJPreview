// ProjectLibraryPage：/projects 工程库页（T33.3 正式版）。
// 组合 useProjects + ProjectLibraryPanel + DeleteProjectDialog + ImportProjectButton。
// 搜索/筛选在 Panel 内（客户端）；删除二次确认；导入成功后跳转新工程工作台。

import { useCallback, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useProjects } from "../features/projects/useProjects";
import type { ProjectSummary } from "../features/projects/projectTypes";
import { DeleteProjectDialog } from "../features/projects/DeleteProjectDialog";
import { BatchDeleteDialog } from "../features/projects/BatchDeleteDialog";
import { ImportProjectButton } from "../features/projects/ImportProjectButton";
import { ProjectLibraryPanel } from "../features/projects/ProjectLibraryPanel";
import { deleteProject as deleteProjectApi, exportProject } from "../features/projects/projectApi";
import { downloadBlob } from "../shared/utils/download";
import { ActionButton, ButtonRow, ErrorState, LoadingState, SectionCard } from "../components/ui";

export default function ProjectLibraryPage() {
  const navigate = useNavigate();
  const { projects, isLoading, error, reload, removeProject } = useProjects();

  const [deleteTarget, setDeleteTarget] = useState<ProjectSummary | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchOpen, setBatchOpen] = useState(false);
  const [batchResult, setBatchResult] = useState<string | null>(null);

  const handleRequestDelete = useCallback((project: ProjectSummary) => {
    setDeleteTarget(project);
    setDeleteError(null);
    setIsDeleting(false);
  }, []);

  const handleCancelDelete = useCallback(() => {
    if (isDeleting) return;
    setDeleteTarget(null);
    setDeleteError(null);
  }, [isDeleting]);

  const handleConfirmDelete = useCallback(async () => {
    if (!deleteTarget || isDeleting) return;
    setIsDeleting(true);
    setDeleteError(null);
    const ok = await removeProject(deleteTarget.songId);
    setIsDeleting(false);
    if (ok) {
      setDeleteTarget(null);
    } else {
      setDeleteError("删除失败，请重试。");
    }
  }, [deleteTarget, isDeleting, removeProject]);

  const handleImported = useCallback(
    async (songId: string) => {
      await reload();
      navigate(`/projects/${encodeURIComponent(songId)}`);
    },
    [navigate, reload],
  );

  const handleExport = useCallback(async (project: ProjectSummary) => {
    try {
      const result = await exportProject(project.songId);
      downloadBlob(result.blob, result.filename);
    } catch (e) {
      // 导出失败静默提示：保持工程库可用
      console.error("导出失败", e);
    }
  }, []);

  const toggleSelect = useCallback((songId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(songId)) {
        next.delete(songId);
      } else {
        next.add(songId);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback((ids: string[]) => {
    setSelectedIds(new Set(ids));
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
    setBatchResult(null);
  }, []);

  const handleBatchDelete = useCallback(() => {
    setBatchResult(null);
    setDeleteError(null);
    setBatchOpen(true);
  }, []);

  const confirmBatchDelete = useCallback(async () => {
    if (selectedIds.size === 0 || isDeleting) return;
    setIsDeleting(true);
    setDeleteError(null);
    setBatchResult(null);
    const ids = [...selectedIds];
    const results = await Promise.allSettled(ids.map((id) => deleteProjectApi(id)));
    const succeeded = ids.filter((_, i) => results[i].status === "fulfilled");
    const failed = ids.filter((_, i) => results[i].status === "rejected");
    setIsDeleting(false);

    if (failed.length === 0) {
      setBatchOpen(false);
      setSelectedIds(new Set());
      await reload();
      return;
    }
    if (succeeded.length > 0) {
      await reload();
    }
    // 部分失败：失败的保持选中，供重试
    setSelectedIds(new Set(failed));
    setBatchResult(
      failed.length === ids.length
        ? `删除失败（${failed.length} 个工程均未删除）。`
        : `已删除 ${succeeded.length} 个工程，${failed.length} 个删除失败。`,
    );
  }, [selectedIds, isDeleting, reload]);

  const selectedProjects = projects.filter((p) => selectedIds.has(p.songId));

  let body;
  if (isLoading && projects.length === 0) {
    body = <LoadingState title="正在加载工程…" />;
  } else if (error && projects.length === 0) {
    body = (
      <ErrorState
        title="工程列表加载失败"
        message={error}
        action={
          <ActionButton variant="secondary" onClick={() => void reload()}>
            重新加载
          </ActionButton>
        }
      />
    );
  } else {
    body = (
      <ProjectLibraryPanel
        projects={projects}
        onDelete={handleRequestDelete}
        onExport={handleExport}
        onRefresh={() => void reload()}
        isRefreshing={isLoading}
        selectedIds={selectedIds}
        onToggleSelect={toggleSelect}
        onSelectAll={selectAll}
        onClearSelection={clearSelection}
        onBatchDelete={handleBatchDelete}
      />
    );
  }

  return (
    <div className="page page--projects">
      <SectionCard
        title="工程库"
        description="历史工程列表"
        actions={
          <ButtonRow>
            <Link to="/create" className="ui-action-button ui-action-button--primary">
              + 新建音乐
            </Link>
            <ImportProjectButton onImported={(songId) => void handleImported(songId)} />
          </ButtonRow>
        }
      >
        {body}
      </SectionCard>

      <DeleteProjectDialog
        open={Boolean(deleteTarget)}
        project={deleteTarget}
        isDeleting={isDeleting}
        error={deleteError}
        onCancel={handleCancelDelete}
        onConfirm={() => void handleConfirmDelete()}
      />

      <BatchDeleteDialog
        open={batchOpen}
        projects={selectedProjects}
        isDeleting={isDeleting}
        error={batchResult}
        onCancel={() => setBatchOpen(false)}
        onConfirm={() => void confirmBatchDelete()}
      />

      {batchResult && (
        <div className="project-library__batch-result" role="status">
          {batchResult}
        </div>
      )}
    </div>
  );
}
