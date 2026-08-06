// StatusBadge：状态徽章（provider 状态 / warning 数量 / MIDI/WAV ready 等）。

import type { ReactNode } from "react";

export type StatusBadgeVariant = "neutral" | "success" | "warning" | "danger" | "info" | "primary";

export interface StatusBadgeProps {
  children: ReactNode;
  variant?: StatusBadgeVariant;
  title?: string;
}

const VARIANT_CLASS: Record<StatusBadgeVariant, string> = {
  neutral: "",
  success: " ui-status-badge--success",
  warning: " ui-status-badge--warning",
  danger: " ui-status-badge--danger",
  info: " ui-status-badge--info",
  primary: " ui-status-badge--primary",
};

export function StatusBadge({ children, variant = "neutral", title }: StatusBadgeProps) {
  return (
    <span className={`ui-status-badge${VARIANT_CLASS[variant]}`} title={title}>
      {children}
    </span>
  );
}
