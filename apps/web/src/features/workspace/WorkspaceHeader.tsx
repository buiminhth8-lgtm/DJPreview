// features/workspace/WorkspaceHeader.tsx（T33.5）
// 工作台顶部：返回工程库 + 工程标题 + 版本 + 资产状态。

import { Link } from "react-router-dom";
import { StatusBadge } from "../../components/ui";

export interface WorkspaceHeaderProps {
  songId: string | null;
  title?: string | null;
  currentVersionId: string | null;
  hasMidi: boolean;
  hasAudio: boolean;
  audioNeedsRender?: boolean;
  renderer?: string | null;
  isFallback?: boolean;
  soundfontName?: string | null;
  error: string | null;
}

export default function WorkspaceHeader({
  songId,
  title,
  currentVersionId,
  hasMidi,
  hasAudio,
  audioNeedsRender = false,
  renderer,
  isFallback = false,
  soundfontName,
  error,
}: WorkspaceHeaderProps) {
  return (
    <header className="workspace-header">
      <div className="workspace-header__titles">
        <Link to="/projects" className="workspace-header__back">
          ← 工程库
        </Link>
        <h1 className="workspace-header__title">{title || "AI Music Studio"}</h1>
        {songId && <p className="workspace-header__subtitle">song_id：{songId.slice(0, 8)}…</p>}
      </div>

      <div className="workspace-header__badges" role="list" aria-label="工作台状态">
        {songId && currentVersionId && (
          <StatusBadge variant="info" title="当前版本">
            版本：{currentVersionId}
          </StatusBadge>
        )}
        {songId && (
          <StatusBadge variant={hasMidi ? "success" : "neutral"} title="MIDI 资产">
            MIDI：{hasMidi ? "有" : "无"}
          </StatusBadge>
        )}
        {songId && (
          <StatusBadge
            variant={hasAudio ? (audioNeedsRender ? "warning" : "success") : "neutral"}
            title="WAV 资产"
          >
            WAV：{hasAudio ? (audioNeedsRender ? "需重新渲染" : "有") : "无"}
          </StatusBadge>
        )}
        {hasAudio && isFallback && <StatusBadge variant="warning">Fallback Renderer</StatusBadge>}
        {renderer === "fluidsynth" && <StatusBadge variant="success">FluidSynth</StatusBadge>}
        {soundfontName && <StatusBadge variant="neutral">SF：{soundfontName}</StatusBadge>}
      </div>

      {error && <p className="workspace-header__error" role="alert">{error}</p>}
    </header>
  );
}
