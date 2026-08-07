// DeleteProjectDialog：删除工程二次确认（T33.3）。
// 删除中禁用重复提交；失败保持打开并显示错误；成功由父级关闭。

import type { ProjectSummary } from "./projectTypes";
import { ActionButton, ButtonRow, InlineNotice } from "../../components/ui";

export interface DeleteProjectDialogProps {
  open: boolean;
  project: ProjectSummary | null;
  isDeleting: boolean;
  error?: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

export function DeleteProjectDialog({
  open,
  project,
  isDeleting,
  error,
  onCancel,
  onConfirm,
}: DeleteProjectDialogProps) {
  if (!open || !project) return null;

  return (
    <div
      className="ui-dialog-backdrop"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !isDeleting) onCancel();
      }}
    >
      <div className="ui-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-dialog-title">
        <h2 className="ui-dialog__title" id="delete-dialog-title">
          删除工程？
        </h2>
        <p className="ui-dialog__body">
          “{project.title || "未命名工程"}” 将被永久删除。
          <br />
          此操作无法撤销。
        </p>

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
            {isDeleting ? "删除中…" : "删除工程"}
          </ActionButton>
        </ButtonRow>
      </div>
    </div>
  );
}
