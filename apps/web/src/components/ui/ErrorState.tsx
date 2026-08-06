// ErrorState：API 错误展示（code / message / requestId / action）。

import type { ReactNode } from "react";

export interface ErrorStateProps {
  title?: string;
  message?: string;
  code?: string;
  requestId?: string;
  action?: ReactNode;
}

export function ErrorState({ title = "请求失败", message, code, requestId, action }: ErrorStateProps) {
  return (
    <div className="ui-error-state" role="alert">
      <div className="ui-error-state__marker" aria-hidden="true">
        ✕
      </div>
      <p className="ui-error-state__title">{title}</p>
      {message && <p className="ui-error-state__message">{message}</p>}
      {(code || requestId) && (
        <div className="ui-error-state__meta">
          {code && <span>code: {code}</span>}
          {code && requestId && <span> · </span>}
          {requestId && <span>request_id: {requestId}</span>}
        </div>
      )}
      {action && <div className="ui-error-state__action">{action}</div>}
    </div>
  );
}
