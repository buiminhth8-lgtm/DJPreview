// 分析领域 API：piano roll、quality check / report / optimize。

import { requestJson } from "./client";
import type { OptimizeResponse, PianoRollData, QualityReport } from "./types";

export function getPianoRoll(songId: string, trackId?: string, maxNotes = 5000): Promise<PianoRollData> {
  const params = new URLSearchParams({ max_notes: String(maxNotes) });
  if (trackId) params.set("track_id", trackId);
  return requestJson(`/api/v1/songs/${songId}/piano-roll?${params.toString()}`, "GET");
}

export function checkQuality(songId: string): Promise<QualityReport> {
  return requestJson(`/api/v1/songs/${songId}/quality/check`, "POST");
}

export function getQualityReport(songId: string): Promise<QualityReport> {
  return requestJson(`/api/v1/songs/${songId}/quality/report`, "GET");
}

export function optimizeArrangement(songId: string, autoRender = true): Promise<OptimizeResponse> {
  return requestJson(`/api/v1/songs/${songId}/quality/optimize`, "POST", { auto_render: autoRender });
}
