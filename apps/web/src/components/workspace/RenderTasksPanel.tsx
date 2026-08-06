// RenderTasksPanel：任务与日志（常驻，T38-H）。
// 无工程时 Empty State；有工程才请求任务列表；展示任务状态/进度/错误/结果资产。
// 专注 render/export tasks，与 T38-E 的 GenerationDebugPanel（LLM 调试）区分。

import { useCallback, useEffect, useState } from "react";
import { listSongTasks } from "../../api/taskApi";
import type { RenderTask } from "../../api/types";
import { ActionButton, ButtonRow, EmptyState, InlineNotice, SectionCard, StatusBadge } from "../ui";
import type { StatusBadgeVariant } from "../ui";

export interface RenderTasksPanelProps {
  songId?: string | null;
  onError?: (message: string) => void;
  onAssetsChanged?: () => void | Promise<void>;
}

const STATUS_VARIANT: Record<string, StatusBadgeVariant> = {
  queued: "neutral",
  running: "info",
  succeeded: "success",
  failed: "danger",
  cancelled: "warning",
};

export function RenderTasksPanel({ songId, onError }: RenderTasksPanelProps) {
  const [tasks, setTasks] = useState<RenderTask[] | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!songId) {
      setTasks(null);
      return null;
    }
    setLoading(true);
    try {
      const list = await listSongTasks(songId);
      setTasks(Array.isArray(list) ? list : []);
      return list;
    } catch (e) {
      onError?.(e instanceof Error ? e.message : String(e));
      return null;
    } finally {
      setLoading(false);
    }
  }, [songId, onError]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  let body;
  if (!songId) {
    body = (
      <EmptyState
        title="暂无任务"
        description="生成或导入工程后，MIDI 渲染、WAV 渲染、Stems 导出等任务会显示在这里。"
      />
    );
  } else if (tasks === null) {
    body = <EmptyState title="当前工程暂无任务" description="执行渲染或导出操作后，任务进度会显示在这里。" />;
  } else if (tasks.length === 0) {
    body = (
      <EmptyState
        title="当前工程暂无任务"
        description="执行渲染或导出操作后，任务进度会显示在这里。"
        action={
          <ButtonRow>
            <ActionButton variant="secondary" onClick={() => void refresh()} disabled={loading} loading={loading}>
              {loading ? "加载中…" : "刷新任务"}
            </ActionButton>
          </ButtonRow>
        }
      />
    );
  } else {
    body = (
      <div className="workspace-render-tasks">
        <ButtonRow className="workspace-render-tasks__toolbar">
          <ActionButton variant="secondary" onClick={() => void refresh()} disabled={loading} loading={loading}>
            {loading ? "加载中…" : "刷新任务"}
          </ActionButton>
        </ButtonRow>
        <TaskStatusList tasks={tasks} />
      </div>
    );
  }

  return (
    <SectionCard title="任务与日志" description="渲染 / 导出任务进度与结果">
      {body}
    </SectionCard>
  );
}

export function TaskStatusList({ tasks }: { tasks: RenderTask[] }) {
  const list = Array.isArray(tasks) ? tasks : [];
  if (list.length === 0) {
    return <div className="muted-note">暂无任务。</div>;
  }
  return (
    <div className="workspace-task-list">
      {list.map((task) => {
        const progress = Math.max(0, Math.min(100, task.progress ?? 0));
        return (
          <div className="workspace-task-card" key={task.task_id}>
            <div className="workspace-task-card__head">
              <span className="workspace-task-card__type">{task.task_type || "—"}</span>
              <StatusBadge variant={STATUS_VARIANT[task.status] ?? "neutral"}>{task.status}</StatusBadge>
              <span className="workspace-task-card__time">
                {task.created_at ? new Date(task.created_at).toLocaleString() : "—"}
              </span>
            </div>
            <div className="workspace-task-card__id">task_id: {task.task_id || "—"}</div>
            {task.message && <div className="workspace-task-card__message">{task.message}</div>}
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>
            <div className="workspace-task-card__progress">{progress}%</div>
            {task.status === "failed" && task.error && (
              <InlineNotice variant="danger">{task.error}</InlineNotice>
            )}
            {task.result && (
              <details className="workspace-task-card__result">
                <summary>任务结果</summary>
                <pre>{JSON.stringify(task.result, null, 2)}</pre>
              </details>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default RenderTasksPanel;
