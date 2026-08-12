// VersionPanel：版本管理（常驻，T38-G）。
// 无工程时 Empty State；有工程但无版本时提示；有版本时列表 + 详情 / diff / restore（带确认）。

import type { VersionInfo } from "../../api/types";
import { ActionButton, ButtonRow, EmptyState, SectionCard, StatusBadge } from "../../components/ui";
import { JsonPreview } from "../../shared/components/JsonPreview";

export interface VersionPanelProps {
  songId?: string | null;
  versions?: VersionInfo[] | null;
  currentVersionId?: string | null;
  loading?: boolean;
  restoring?: boolean;
  selectedDetail?: unknown;
  selectedDiff?: unknown;
  onLoad?: () => void;
  onRestore?: (versionId: string) => void;
  onViewDetail?: (versionId: string) => void;
  onViewDiff?: (versionId: string) => void;
}

export function VersionPanel({
  songId,
  versions,
  currentVersionId,
  loading = false,
  restoring = false,
  selectedDetail,
  selectedDiff,
  onLoad,
  onRestore,
  onViewDetail,
  onViewDiff,
}: VersionPanelProps) {
  const list = Array.isArray(versions) ? versions : null;

  let body;
  if (!songId) {
    body = (
      <EmptyState title="暂无版本" description="生成或导入工程后会自动创建 v1。" />
    );
  } else if (list === null || list.length === 0) {
    body = (
      <EmptyState
        title="当前工程暂无版本记录"
        description="完成生成或编辑后将自动记录版本。"
        action={
          <ButtonRow>
            <ActionButton variant="secondary" onClick={onLoad} disabled={!songId} disabledReason={!songId ? "请先生成或导入工程" : undefined}>
              刷新版本
            </ActionButton>
          </ButtonRow>
        }
      />
    );
  } else {
    body = (
      <div className="workspace-versions">
        <ButtonRow className="workspace-versions__toolbar">
          <ActionButton variant="secondary" onClick={onLoad} disabled={loading} loading={loading}>
            {loading ? "加载中…" : "刷新版本"}
          </ActionButton>
        </ButtonRow>
        <div className="workspace-version-list">
          {[...list].reverse().map((v) => {
            const isCurrent = v.version_id === currentVersionId;
            return (
              <div className={`workspace-version-item${isCurrent ? " current" : ""}`} key={v.version_id}>
                <div className="workspace-version-item__head">
                  <span className="workspace-version-item__number">v{v.version_number}</span>
                  {isCurrent && <StatusBadge variant="success">当前</StatusBadge>}
                  <span className="workspace-version-item__time">{v.created_at ? new Date(v.created_at).toLocaleString() : "—"}</span>
                </div>
                <div className="workspace-version-item__detail">{v.instruction ?? "初始版本"}</div>
                <ButtonRow className="workspace-version-item__actions">
                  {onViewDetail && (
                    <ActionButton variant="ghost" onClick={() => onViewDetail(v.version_id)} disabled={!v.version_id} disabledReason={!v.version_id ? "版本信息不可用" : undefined}>
                      查看详情
                    </ActionButton>
                  )}
                  {onViewDiff && (
                    <ActionButton variant="ghost" onClick={() => onViewDiff(v.version_id)} disabled={!v.version_id} disabledReason={!v.version_id ? "版本信息不可用" : undefined}>
                      查看 Diff
                    </ActionButton>
                  )}
                  {!isCurrent && onRestore && (
                    <ActionButton
                      variant="danger"
                      onClick={() => onRestore(v.version_id)}
                      disabled={restoring}
                      loading={restoring}
                    >
                      {restoring ? "恢复中…" : "恢复此版本"}
                    </ActionButton>
                  )}
                </ButtonRow>
              </div>
            );
          })}
        </div>
        {selectedDetail != null && (
          <div className="workspace-versions__detail">
            <h3>版本详情</h3>
            <JsonPreview value={selectedDetail} maxHeight={240} />
          </div>
        )}
        {selectedDiff != null && (
          <div className="workspace-versions__diff">
            <h3>Diff</h3>
            <JsonPreview value={selectedDiff} maxHeight={240} />
          </div>
        )}
      </div>
    );
  }

  return (
    <SectionCard
      title="版本管理"
      description="版本列表 / 详情 / Diff / 恢复"
      badge={list && list.length > 0 ? <StatusBadge variant="info">{list.length} versions</StatusBadge> : undefined}
    >
      {body}
    </SectionCard>
  );
}

export default VersionPanel;
