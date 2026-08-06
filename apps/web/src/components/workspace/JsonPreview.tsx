// JsonPreview：统一 JSON 展示（可滚动 + 复制 + 空状态）。
// 使用原生 <pre>，不引入大型 JSON viewer 依赖。

import { useState } from "react";
import { EmptyState } from "../ui";

export interface JsonPreviewProps {
  value?: unknown;
  emptyTitle?: string;
  emptyDescription?: string;
  maxHeight?: number;
}

export function JsonPreview({
  value,
  emptyTitle = "暂无数据",
  emptyDescription,
  maxHeight = 420,
}: JsonPreviewProps) {
  const [copied, setCopied] = useState(false);

  if (value === undefined || value === null) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  let text: string;
  try {
    text = JSON.stringify(value, null, 2);
  } catch {
    text = String(value);
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // 剪贴板不可用时静默忽略
    }
  };

  return (
    <div className="workspace-json-preview">
      <div className="workspace-json-preview__toolbar">
        <span className="workspace-json-preview__meta">{text.length} chars</span>
        <button className="copy-btn" onClick={() => void handleCopy()}>
          {copied ? "已复制" : "复制 JSON"}
        </button>
      </div>
      <pre className="workspace-json-preview__body" style={{ maxHeight }}>
        {text}
      </pre>
    </div>
  );
}
