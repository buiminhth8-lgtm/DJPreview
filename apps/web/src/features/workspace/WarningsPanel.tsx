// WarningsPanel：校验 warning 列表。
// 始终显示；无 MusicSpec 或 warnings 为空时显示对应状态；支持字符串与结构化 warning。

import { EmptyState, InlineNotice, SectionCard, StatusBadge } from "../../components/ui";
import type { StatusBadgeVariant } from "../../components/ui";

export type WarningLike =
  | string
  | {
      code?: string;
      message?: string;
      stage?: string;
      severity?: string;
      section?: string;
      track_id?: string;
      details?: unknown;
    };

export interface WarningsPanelProps {
  warnings?: WarningLike[] | null;
  hasMusicSpec?: boolean;
}

function severityVariant(severity?: string): StatusBadgeVariant {
  switch ((severity ?? "warning").toLowerCase()) {
    case "error":
      return "danger";
    case "info":
      return "info";
    default:
      return "warning";
  }
}

export function WarningsPanel({ warnings, hasMusicSpec = false }: WarningsPanelProps) {
  const list = warnings ?? [];
  const normalized: Array<{ code?: string; message: string; stage?: string; severity?: string }> = list.map(
    (w) => {
      if (typeof w === "string") return { message: w };
      return {
        code: w.code,
        message: w.message || String(w.details ?? ""),
        stage: w.stage,
        severity: w.severity,
      };
    },
  );

  let body;
  if (!hasMusicSpec) {
    body = (
      <EmptyState
        title="暂无校验结果"
        description="生成 MusicSpec 后将在这里显示结构、和声、乐器等 warning。"
      />
    );
  } else if (normalized.length === 0) {
    body = (
      <InlineNotice variant="success" title="当前没有校验警告">
        MusicSpec 结构看起来正常。
      </InlineNotice>
    );
  } else {
    body = (
      <ul className="workspace-warning-list">
        {normalized.map((w, i) => (
          <li key={i} className="workspace-warning-list__item">
            <StatusBadge variant={severityVariant(w.severity)}>{w.severity ?? "warning"}</StatusBadge>
            {w.code && <code className="workspace-warning-list__code">{w.code}</code>}
            <span className="workspace-warning-list__message">{w.message}</span>
            {w.stage && <span className="workspace-warning-list__stage">stage: {w.stage}</span>}
          </li>
        ))}
      </ul>
    );
  }

  return (
    <SectionCard
      title="Warnings"
      description="MusicSpec 结构、和声、乐器校验提示"
      badge={
        normalized.length > 0 ? (
          <StatusBadge variant="warning">{normalized.length} warnings</StatusBadge>
        ) : undefined
      }
    >
      {body}
    </SectionCard>
  );
}
