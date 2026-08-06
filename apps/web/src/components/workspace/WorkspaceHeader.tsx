// 工作台头部：AI Music Studio + Provider / Model / 当前工程状态。
// Provider / Model 前端暂不感知，显示「未知 / 当前环境」，后续可增强。

import { StatusBadge } from "../ui";
import StatusMessage from "./StatusMessage";

export interface WorkspaceHeaderProps {
  songId: string | null;
  currentVersionId: string | null;
  hasMidi: boolean;
  hasAudio: boolean;
  error: string | null;
}

export default function WorkspaceHeader({
  songId,
  currentVersionId,
  hasMidi,
  hasAudio,
  error,
}: WorkspaceHeaderProps) {
  return (
    <header className="workspace-header">
      <div className="workspace-header__titles">
        <h1 className="workspace-header__title">AI Music Studio</h1>
        <p className="workspace-header__subtitle">自然语言生成、编辑、试听和导出音乐工程</p>
      </div>

      <div className="workspace-header__badges" role="list" aria-label="工作台状态">
        <StatusBadge variant="primary" title="当前 LLM Provider">
          Provider：当前环境 / 未知
        </StatusBadge>
        <StatusBadge variant="neutral" title="当前模型">
          Model：未知
        </StatusBadge>
        {songId ? (
          <>
            <StatusBadge variant="info" title="当前工程">
              工程：{songId.slice(0, 8)}…
            </StatusBadge>
            {currentVersionId && (
              <StatusBadge variant="info" title="当前版本">
                版本：{currentVersionId}
              </StatusBadge>
            )}
            <StatusBadge variant={hasMidi ? "success" : "neutral"} title="MIDI 资产">
              MIDI：{hasMidi ? "有" : "无"}
            </StatusBadge>
            <StatusBadge variant={hasAudio ? "success" : "neutral"} title="WAV 资产">
              WAV：{hasAudio ? "有" : "无"}
            </StatusBadge>
          </>
        ) : (
          <StatusBadge variant="neutral" title="尚未创建工程">
            状态：未生成
          </StatusBadge>
        )}
      </div>

      <StatusMessage error={error} />
    </header>
  );
}
