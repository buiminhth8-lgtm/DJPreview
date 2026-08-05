// useRenderTasks：启动异步渲染任务并轮询进度。

import { useCallback, useEffect, useRef, useState } from "react";

import {
  cancelTask,
  getTask,
  startAudioRenderTask,
  startMidiRenderTask,
  startStemsExportTask,
} from "../api/taskApi";
import type { RenderTask } from "../api/types";
import { getErrorMessage } from "./error";

const POLL_INTERVAL_MS = 1000;
const TERMINAL_STATUSES = new Set(["succeeded", "failed", "cancelled"]);

export function useRenderTasks(
  songId?: string | null,
  onAssetsChanged?: () => void | Promise<void>,
) {
  const [task, setTask] = useState<RenderTask | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);
  const onAssetsChangedRef = useRef(onAssetsChanged);
  onAssetsChangedRef.current = onAssetsChanged;

  const stopPolling = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const pollTask = useCallback(
    (taskId: string) => {
      stopPolling();
      timerRef.current = window.setInterval(() => {
        void getTask(taskId)
          .then(async (updated) => {
            setTask(updated);
            if (TERMINAL_STATUSES.has(updated.status)) {
              stopPolling();
              if (updated.status === "succeeded") {
                await onAssetsChangedRef.current?.();
              } else if (updated.status === "failed") {
                setError(updated.error ?? "任务失败");
              }
            }
          })
          .catch((e: unknown) => {
            setError(getErrorMessage(e));
            stopPolling();
          });
      }, POLL_INTERVAL_MS);
    },
    [stopPolling],
  );

  const startTask = useCallback(
    async (starter: (id: string) => Promise<RenderTask>): Promise<RenderTask | null> => {
      if (!songId) return null;
      setError(null);
      try {
        const created = await starter(songId);
        setTask(created);
        if (TERMINAL_STATUSES.has(created.status)) {
          if (created.status === "succeeded") {
            await onAssetsChangedRef.current?.();
          }
          return created;
        }
        pollTask(created.task_id);
        return created;
      } catch (e) {
        setError(getErrorMessage(e));
        return null;
      }
    },
    [songId, pollTask],
  );

  const startMidi = useCallback(() => startTask(startMidiRenderTask), [startTask]);
  const startAudio = useCallback(
    (options?: { soundfont_id?: string | null }) => startTask((id) => startAudioRenderTask(id, options)),
    [startTask],
  );
  const startStems = useCallback(() => startTask(startStemsExportTask), [startTask]);

  const cancel = useCallback(async (): Promise<RenderTask | null> => {
    if (!task) return null;
    try {
      const updated = await cancelTask(task.task_id);
      setTask(updated);
      if (updated.status !== "running") {
        stopPolling();
      }
      return updated;
    } catch (e) {
      setError(getErrorMessage(e));
      return null;
    }
  }, [task, stopPolling]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  return {
    task,
    error,
    setError,
    startMidi,
    startAudio,
    startStems,
    cancel,
    stopPolling,
  };
}
