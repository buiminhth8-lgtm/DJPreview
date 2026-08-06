// SectionCard：工作台每个模块的统一卡片容器。

import type { ReactNode } from "react";
import { PanelHeader } from "./PanelHeader";

export interface SectionCardProps {
  title?: string;
  description?: string;
  eyebrow?: string;
  badge?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  compact?: boolean;
  muted?: boolean;
}

export function SectionCard({
  title,
  description,
  eyebrow,
  badge,
  actions,
  children,
  className,
  compact,
  muted,
}: SectionCardProps) {
  const classes = [
    "ui-section-card",
    compact ? "ui-section-card--compact" : "",
    muted ? "ui-section-card--muted" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <section className={classes}>
      {title !== undefined && (
        <PanelHeader title={title} description={description} eyebrow={eyebrow} badge={badge} actions={actions} />
      )}
      <div className="ui-section-card__body">{children}</div>
    </section>
  );
}
