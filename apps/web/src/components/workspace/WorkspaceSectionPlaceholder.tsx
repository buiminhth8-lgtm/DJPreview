// WorkspaceSectionPlaceholder：后续模块的统一常驻占位卡片。
// 内部使用 T38-B 的 SectionCard + EmptyState + StatusBadge。

import type { ReactNode } from "react";
import { EmptyState, SectionCard, StatusBadge } from "../ui";
import type { StatusBadgeVariant } from "../ui";

export interface WorkspaceSectionPlaceholderProps {
  title: string;
  description?: string;
  emptyTitle: string;
  emptyDescription: string;
  badgeLabel?: string;
  badgeVariant?: StatusBadgeVariant;
  actions?: ReactNode;
}

export function WorkspaceSectionPlaceholder({
  title,
  description,
  emptyTitle,
  emptyDescription,
  badgeLabel,
  badgeVariant = "neutral",
  actions,
}: WorkspaceSectionPlaceholderProps) {
  return (
    <SectionCard
      title={title}
      description={description}
      badge={badgeLabel ? <StatusBadge variant={badgeVariant}>{badgeLabel}</StatusBadge> : undefined}
    >
      <EmptyState title={emptyTitle} description={emptyDescription} action={actions} />
    </SectionCard>
  );
}
