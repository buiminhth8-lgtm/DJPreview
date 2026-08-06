// ActionButton：带 loading / disabled 原因提示的标准按钮。

import type { ButtonHTMLAttributes } from "react";

export type ActionButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "success";

export interface ActionButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ActionButtonVariant;
  loading?: boolean;
  disabledReason?: string;
}

const VARIANT_CLASS: Record<ActionButtonVariant, string> = {
  primary: " ui-action-button--primary",
  secondary: " ui-action-button--secondary",
  ghost: " ui-action-button--ghost",
  danger: " ui-action-button--danger",
  success: " ui-action-button--success",
};

export function ActionButton({
  variant = "primary",
  loading = false,
  disabledReason,
  disabled,
  className,
  children,
  ...rest
}: ActionButtonProps) {
  const isDisabled = disabled || loading;
  const title = disabledReason && isDisabled ? disabledReason : rest.title;

  return (
    <button
      {...rest}
      className={`ui-action-button${VARIANT_CLASS[variant]}${className ? ` ${className}` : ""}`}
      disabled={isDisabled}
      title={title}
    >
      {loading && <span className="ui-action-button__spinner" aria-hidden="true" />}
      {children}
    </button>
  );
}
