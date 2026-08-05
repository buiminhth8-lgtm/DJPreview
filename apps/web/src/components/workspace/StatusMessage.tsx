// 通用状态提示：error / success / warning。

export interface StatusMessageProps {
  error?: string | null;
  success?: string | null;
  warning?: string | null;
}

export default function StatusMessage({ error, success, warning }: StatusMessageProps) {
  if (error) return <div className="error">⚠ {error}</div>;
  if (success) return <div className="success">✓ {success}</div>;
  if (warning) return <div className="warning">⚠ {warning}</div>;
  return null;
}
