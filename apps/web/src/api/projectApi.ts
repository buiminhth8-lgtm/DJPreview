// 工程导入导出领域 API（.aimusic.zip）。

import { API_BASE_URL, requestForm } from "./client";
import type { ProjectImportResponse } from "./types";

export function exportProjectUrl(songId: string): string {
  return `${API_BASE_URL}/api/v1/songs/${songId}/project/export`;
}

export function getProjectExportUrl(songId: string): string {
  return exportProjectUrl(songId);
}

export function importProject(file: File): Promise<ProjectImportResponse> {
  const form = new FormData();
  form.append("file", file);
  return requestForm("/api/v1/projects/import", form);
}
