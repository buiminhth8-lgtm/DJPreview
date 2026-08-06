// EmptyState：无数据占位（半透明内框 + 虚线边框 + 可选 action）。

import type { ReactNode } from "react";

export interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  compact?: boolean;
}

export function EmptyState({ title, description, icon, action, compact }: EmptyStateProps) {
  return (
    <div className={`ui-empty-state${compact ? " ui-empty-state--compact" : ""}`}>
      {icon && <div className="ui-empty-state__icon" aria-hidden="true">{icon}</div>}
      <p className="ui-empty-state__title">{title}</p>
      {description && <p className="ui-empty-state__description">{description}</p>}
      {action && <div className="ui-empty-state__action">{action}</div>}
    </div>
  );
}
