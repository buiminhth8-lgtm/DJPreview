// ButtonRow：统一按钮排列。

import type { ReactNode } from "react";

export interface ButtonRowProps {
  children: ReactNode;
  align?: "left" | "right" | "between";
  wrap?: boolean;
  className?: string;
}

export function ButtonRow({ children, align = "left", wrap = true, className }: ButtonRowProps) {
  const alignClass = align === "right" ? " ui-button-row--right" : align === "between" ? " ui-button-row--between" : "";
  const wrapClass = wrap ? " ui-button-row--wrap" : "";
  return <div className={`ui-button-row${alignClass}${wrapClass}${className ? ` ${className}` : ""}`}>{children}</div>;
}
