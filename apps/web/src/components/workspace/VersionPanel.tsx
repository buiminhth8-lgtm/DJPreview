// 版本面板：列表 / 当前标识 / 恢复。

import type { VersionInfo } from "../../api/types";

export interface VersionPanelProps {
  versions: VersionInfo[] | null;
  currentVersionId: string | null;
  loading: boolean;
  onLoad: () => void;
  onRestore: (versionId: string) => void;
}

export default function VersionPanel({
  versions,
  currentVersionId,
  loading,
  onLoad,
  onRestore,
}: VersionPanelProps) {
  return (
    <section className="panel result">
      <h2>版本管理</h2>
      <div className="actions">
        <button onClick={onLoad} disabled={loading}>
          {loading ? "加载中…" : "查看版本"}
        </button>
      </div>
      {versions && (
        <div className="version-list">
          {[...versions].reverse().map((v) => (
            <div
              className={`version-item${v.version_id === currentVersionId ? " current" : ""}`}
              key={v.version_id}
            >
              <div className="version-head">
                <span className="version-number">v{v.version_number}</span>
                {v.version_id === currentVersionId && <span className="version-current">当前</span>}
              </div>
              <div className="version-detail">
                {v.instruction ?? "初始版本"} · {new Date(v.created_at).toLocaleString()}
              </div>
              {v.version_id !== currentVersionId && (
                <button className="restore-btn" onClick={() => onRestore(v.version_id)}>
                  恢复此版本
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
