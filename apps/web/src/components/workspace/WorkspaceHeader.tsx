// 工作台头部：项目标题 + 当前状态摘要。

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
    <header>
      <h1>AI Music MVP</h1>
      <p className="subtitle">
        生成 → MIDI → WAV → 修改/版本 → 混音/可视化/质量 → 风格/参考/重生成/评估
      </p>
      {songId && (
        <div className="status-line">
          <span className="status-chip">song_id：{songId.slice(0, 8)}…</span>
          {currentVersionId && <span className="status-chip">当前版本：{currentVersionId}</span>}
          <span className={`status-chip${hasMidi ? " ok" : ""}`}>MIDI：{hasMidi ? "有" : "无"}</span>
          <span className={`status-chip${hasAudio ? " ok" : ""}`}>WAV：{hasAudio ? "有" : "无"}</span>
        </div>
      )}
      <StatusMessage error={error} />
    </header>
  );
}
