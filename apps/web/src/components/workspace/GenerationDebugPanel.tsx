// GenerationDebugPanel：生成 MusicSpec 调试信息面板（T35 / T38-E）。
// 常驻显示：无请求时 Empty State；有请求时展示 request_id / provider / model / error /
// debug 元数据 / raw response 路径。默认折叠，出错时自动展开。

import { useEffect, useState } from "react";

import type { GenerationDebug, WarningItem } from "../../api/types";
import type { GenerationErrorInfo, GenerationLogEntry, GenerationStatus } from "../../hooks/useSongProject";
import { EmptyState, SectionCard } from "../ui";

export interface GenerationDebugPanelProps {
  status: GenerationStatus;
  log: GenerationLogEntry[];
  requestId: string | null;
  debug: GenerationDebug | null;
  warnings: WarningItem[];
  errorInfo: GenerationErrorInfo | null;
}

const STATUS_LABEL: Record<GenerationStatus, string> = {
  idle: "idle",
  sending: "sending…",
  success: "success",
  failed: "failed",
};

export default function GenerationDebugPanel({
  status,
  log,
  requestId,
  debug,
  warnings,
  errorInfo,
}: GenerationDebugPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [rawPreviewOpen, setRawPreviewOpen] = useState(false);

  // 出错时自动展开
  useEffect(() => {
    if (status === "failed") setExpanded(true);
  }, [status]);

  const hasData = status !== "idle" || log.length > 0 || Boolean(requestId || debug || errorInfo);

  if (!hasData) {
    return (
      <SectionCard title="调试日志" description="请求与响应诊断">
        <EmptyState
          title="暂无请求日志"
          description="生成 MusicSpec、MIDI 或 WAV 后，请求信息会显示在这里。"
        />
      </SectionCard>
    );
  }

  const hasError = status === "failed";
  const statusClass = hasError ? "status-error" : status === "success" ? "status-ok" : "status-pending";

  const copyText = async (text: string | null | undefined) => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // 剪贴板不可用时静默忽略
    }
  };

  const errorSummary = errorInfo
    ? `${errorInfo.code ?? ""}${errorInfo.stage ? ` [${errorInfo.stage}]` : ""} ${errorInfo.message}`.trim()
    : "";

  return (
    <SectionCard
      title="调试日志"
      description="请求与响应诊断"
      badge={
        hasError ? (
          <span className="status-chip status-error">{STATUS_LABEL[status]}</span>
        ) : (
          <span className={`status-chip ${statusClass}`}>{STATUS_LABEL[status]}</span>
        )
      }
    >
      <details
        className={`debug-panel ${statusClass}`}
        open={expanded}
        onToggle={(e) => setExpanded((e.target as HTMLDetailsElement).open)}
      >
        <summary>
          <span className="debug-title">生成调试</span>
          {requestId && <span className="debug-request-id">req: {requestId}</span>}
        </summary>
        <div className="debug-body">
        <div className="debug-row">
          <span className="debug-label">request_id</span>
          <code className="debug-value">{requestId || "-"}</code>
          {requestId && (
            <button className="copy-btn" onClick={() => void copyText(requestId)}>
              复制
            </button>
          )}
        </div>
        <div className="debug-row">
          <span className="debug-label">provider</span>
          <code className="debug-value">{debug?.provider || "-"}</code>
        </div>
        <div className="debug-row">
          <span className="debug-label">model</span>
          <code className="debug-value">{debug?.model || "-"}</code>
        </div>

        {debug && (
          <div className="debug-meta">
            <div className="debug-row">
              <span className="debug-label">llm_duration_ms</span>
              <code className="debug-value">{debug.llm_duration_ms ?? "-"}</code>
            </div>
            <div className="debug-row">
              <span className="debug-label">validation_warnings</span>
              <code className="debug-value">{debug.validation_warning_count ?? 0}</code>
            </div>
          </div>
        )}

        {hasError && errorInfo && (
          <div className="debug-error-box">
            <div className="debug-row">
              <span className="debug-label">error.code</span>
              <code className="debug-value">{errorInfo.code || "-"}</code>
            </div>
            <div className="debug-row">
              <span className="debug-label">error.stage</span>
              <code className="debug-value">{errorInfo.stage || "-"}</code>
            </div>
            <div className="debug-row">
              <span className="debug-label">error.status</span>
              <code className="debug-value">{errorInfo.status || "-"}</code>
            </div>
            <div className="debug-row">
              <span className="debug-label">error.message</span>
              <code className="debug-value">{errorInfo.message}</code>
            </div>
            {errorInfo.provider && (
              <div className="debug-row">
                <span className="debug-label">provider</span>
                <code className="debug-value">{errorInfo.provider}</code>
              </div>
            )}
            {errorInfo.finish_reason && (
              <div className="debug-row">
                <span className="debug-label">finish_reason</span>
                <code className="debug-value">{errorInfo.finish_reason}</code>
              </div>
            )}
            {errorInfo.content_chars != null && (
              <div className="debug-row">
                <span className="debug-label">content_chars</span>
                <code className="debug-value">{errorInfo.content_chars}</code>
              </div>
            )}
            {errorInfo.hint && (
              <div className="debug-row">
                <span className="debug-label">hint</span>
                <code className="debug-value">{errorInfo.hint}</code>
              </div>
            )}
            {(errorInfo.raw_response_path || errorInfo.message_content_path) && (
              <div className="debug-row">
                <span className="debug-label">raw saved</span>
                <div className="debug-value">
                  <div>LLM 原始响应已保存：</div>
                  {errorInfo.raw_response_path && <div className="debug-path">{errorInfo.raw_response_path}</div>}
                  {errorInfo.message_content_path && <div className="debug-path">{errorInfo.message_content_path}</div>}
                </div>
              </div>
            )}
            {errorSummary && (
              <button className="copy-btn" onClick={() => void copyText(errorSummary)}>
                复制错误摘要
              </button>
            )}
          </div>
        )}

        {warnings.length > 0 && (
          <div className="debug-warnings-box">
            <span className="debug-label">warnings</span>
            <ul>
              {warnings.map((w, i) => (
                <li key={i} className="warning">
                  ⚠ {w.message} {w.code ? `(${w.code})` : ""}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="debug-log-box">
          <span className="debug-label">阶段日志</span>
          <ul>
            {log.map((entry, i) => (
              <li key={i} className={`log-${entry.level}`}>
                <span className="log-level">{entry.level}</span> {entry.message}
                {entry.code && <span className="log-code"> [{entry.code}]</span>}
                {entry.stage && <span className="log-code"> stage={entry.stage}</span>}
                {entry.requestId && <span className="log-code"> req={entry.requestId}</span>}
              </li>
            ))}
          </ul>
        </div>

        {(errorInfo?.rawBodyPreview || (debug && requestId)) && (
          <button className="raw-toggle" onClick={() => setRawPreviewOpen((o) => !o)}>
            {rawPreviewOpen ? "收起 raw preview" : "展开 raw preview"}
          </button>
        )}
        {rawPreviewOpen && (
          <pre className="debug-raw-preview">{errorInfo?.rawBodyPreview || JSON.stringify(debug, null, 2)}</pre>
        )}
      </div>
    </details>
    </SectionCard>
  );
}
