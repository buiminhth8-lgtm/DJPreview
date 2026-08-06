// PanelHeader：工作台模块头部（标题 / 说明 / eyebrow / badge / actions）。

import type { ReactNode } from "react";

export interface PanelHeaderProps {
  title: string;
  description?: string;
  eyebrow?: string;
  badge?: ReactNode;
  actions?: ReactNode;
}

export function PanelHeader({ title, description, eyebrow, badge, actions }: PanelHeaderProps) {
  return (
    <header className="ui-section-card__header">
      <div className="ui-section-card__headings">
        {eyebrow && <p className="ui-section-card__eyebrow">{eyebrow}</p>}
        <h2 className="ui-section-card__title">{title}</h2>
        {description && <p className="ui-section-card__description">{description}</p>}
      </div>
      {badge && <div className="ui-section-card__badge">{badge}</div>}
      {actions && <div className="ui-section-card__actions">{actions}</div>}
    </header>
  );
}
