// BatchDeleteDialog：批量删除工程二次确认（T33-UI1）。
// 展示数量与前几项标题；删除中禁用按钮防重复提交；失败保持打开并显示错误。

import type { ProjectSummary } from "./projectTypes";
import { ActionButton, ButtonRow, InlineNotice } from "../../components/ui";

export interface BatchDeleteDialogProps {
  open: boolean;
  projects: ProjectSummary[];
  isDeleting: boolean;
  error?: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

export function BatchDeleteDialog({
  open,
  projects,
  isDeleting,
  error,
  onCancel,
  onConfirm,
}: BatchDeleteDialogProps) {
  if (!open || projects.length === 0) return null;

  const preview = projects.slice(0, 3).map((p) => p.title || "未命名工程");
  const extraCount = projects.length - preview.length;

  return (
    <div
      className="ui-dialog-backdrop"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !isDeleting) onCancel();
      }}
    >
      <div className="ui-dialog" role="dialog" aria-modal="true" aria-labelledby="batch-delete-title">
        <h2 className="ui-dialog__title" id="batch-delete-title">
          批量删除工程？
        </h2>
        <p className="ui-dialog__body">
          即将永久删除 {projects.length} 个工程。
          <br />
          此操作无法撤销。
        </p>
        <ul className="ui-dialog__preview">
          {preview.map((title) => (
            <li key={title}>{title}</li>
          ))}
          {extraCount > 0 && <li>…以及另外 {extraCount} 个工程</li>}
        </ul>

        {error && (
          <InlineNotice variant="danger" title="删除失败">
            {error}
          </InlineNotice>
        )}

        <ButtonRow className="ui-dialog__actions">
          <ActionButton variant="secondary" onClick={onCancel} disabled={isDeleting}>
            取消
          </ActionButton>
          <ActionButton variant="danger" onClick={onConfirm} loading={isDeleting} disabled={isDeleting}>
            {isDeleting ? "删除中…" : `删除 ${projects.length} 个工程`}
          </ActionButton>
        </ButtonRow>
      </div>
    </div>
  );
}
