// 异步渲染任务面板：MIDI / WAV / stems + 进度条。

import { useEffect } from "react";

import { useRenderTasks } from "../../hooks";

export interface RenderTasksPanelProps {
  songId: string;
  onAssetsChanged?: () => void | Promise<void>;
  onError?: (message: string) => void;
}

const BUSY_STATUSES = new Set(["queued", "running"]);

export default function RenderTasksPanel({ songId, onAssetsChanged, onError }: RenderTasksPanelProps) {
  const tasks = useRenderTasks(songId, onAssetsChanged);

  useEffect(() => {
    if (tasks.error) onError?.(tasks.error);
  }, [tasks.error, onError]);

  const status = tasks.task?.status;
  const busy = status !== undefined && BUSY_STATUSES.has(status);
  const progress = tasks.task?.progress ?? 0;

  return (
    <section className="panel result">
      <h2>异步渲染任务</h2>
      <div className="actions">
        <button onClick={() => void tasks.startMidi()} disabled={busy}>
          {status === "running" && tasks.task?.task_type === "midi" ? "MIDI 渲染中…" : "异步生成 MIDI"}
        </button>
        <button onClick={() => void tasks.startAudio()} disabled={busy}>
          {status === "running" && tasks.task?.task_type === "audio" ? "WAV 渲染中…" : "异步渲染 WAV"}
        </button>
        <button onClick={() => void tasks.startStems()} disabled={busy}>
          {status === "running" && tasks.task?.task_type === "stems" ? "stems 导出中…" : "异步导出 stems"}
        </button>
        {busy && (
          <button onClick={() => void tasks.cancel()} className="danger-btn">
            取消任务
          </button>
        )}
      </div>
      {tasks.task && (
        <div className="task-status">
          <div className="summary-row">
            <span className="summary-label">task_id</span>
            <span className="summary-value">{tasks.task.task_id}</span>
          </div>
          <div className="summary-row">
            <span className="summary-label">状态</span>
            <span className="summary-value">{tasks.task.status}</span>
          </div>
          {tasks.task.message && (
            <div className="summary-row">
              <span className="summary-label">信息</span>
              <span className="summary-value">{tasks.task.message}</span>
            </div>
          )}
          {tasks.task.status === "failed" && tasks.task.error && (
            <div className="error">✗ {tasks.task.error}</div>
          )}
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${Math.max(0, Math.min(100, progress))}%` }} />
          </div>
          <div className="summary-row">
            <span className="summary-label">进度</span>
            <span className="summary-value">{progress}%</span>
          </div>
        </div>
      )}
    </section>
  );
}
