// InlineNotice：内联提示（info / success / warning / danger）。

import type { ReactNode } from "react";

export type InlineNoticeVariant = "info" | "success" | "warning" | "danger";

export interface InlineNoticeProps {
  variant?: InlineNoticeVariant;
  title?: string;
  children: ReactNode;
}

const VARIANT_CLASS: Record<InlineNoticeVariant, string> = {
  info: " ui-inline-notice--info",
  success: " ui-inline-notice--success",
  warning: " ui-inline-notice--warning",
  danger: " ui-inline-notice--danger",
};

const MARKER: Record<InlineNoticeVariant, string> = {
  info: "ℹ",
  success: "✓",
  warning: "⚠",
  danger: "✕",
};

export function InlineNotice({ variant = "info", title, children }: InlineNoticeProps) {
  return (
    <div className={`ui-inline-notice${VARIANT_CLASS[variant]}`} role={variant === "danger" ? "alert" : "note"}>
      <span className="ui-inline-notice__marker" aria-hidden="true">
        {MARKER[variant]}
      </span>
      <div className="ui-inline-notice__content">
        {title && <p className="ui-inline-notice__title">{title}</p>}
        <div>{children}</div>
      </div>
    </div>
  );
}
