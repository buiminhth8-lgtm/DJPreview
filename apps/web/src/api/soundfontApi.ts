// SoundFont / 音源管理领域 API。

import { requestJson } from "./client";
import type {
  ProjectSoundfontRequest,
  ProjectSoundfontResponse,
  SoundfontDiagnosticsResponse,
  SoundfontListResponse,
} from "./types";

export function listSoundfonts(): Promise<SoundfontListResponse> {
  return requestJson("/api/v1/soundfonts", "GET");
}

export function scanSoundfonts(): Promise<SoundfontListResponse> {
  return requestJson("/api/v1/soundfonts/scan", "POST");
}

export function getSoundfontDiagnostics(): Promise<SoundfontDiagnosticsResponse> {
  return requestJson("/api/v1/soundfonts/diagnostics", "GET");
}

export function getProjectSoundfont(songId: string): Promise<ProjectSoundfontResponse> {
  return requestJson(`/api/v1/songs/${songId}/soundfont`, "GET");
}

export function setProjectSoundfont(
  songId: string,
  request: ProjectSoundfontRequest,
): Promise<ProjectSoundfontResponse> {
  return requestJson(`/api/v1/songs/${songId}/soundfont`, "PUT", request);
}
