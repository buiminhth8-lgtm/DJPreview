// 异步渲染任务领域 API。

import { requestJson } from "./client";
import type { RenderTask } from "./types";

export function startMidiRenderTask(songId: string): Promise<RenderTask> {
  return requestJson(`/api/v1/songs/${songId}/tasks/render-midi`, "POST");
}

export function startAudioRenderTask(
  songId: string,
  options?: { soundfont_id?: string | null },
): Promise<RenderTask> {
  return requestJson(`/api/v1/songs/${songId}/tasks/render-audio`, "POST", options ?? undefined);
}

export function startStemsExportTask(songId: string): Promise<RenderTask> {
  return requestJson(`/api/v1/songs/${songId}/tasks/export-stems`, "POST");
}

export function getTask(taskId: string): Promise<RenderTask> {
  return requestJson(`/api/v1/tasks/${taskId}`, "GET");
}

export function listSongTasks(songId: string): Promise<RenderTask[]> {
  return requestJson(`/api/v1/songs/${songId}/tasks`, "GET");
}

export function cancelTask(taskId: string): Promise<RenderTask> {
  return requestJson(`/api/v1/tasks/${taskId}`, "DELETE");
}
