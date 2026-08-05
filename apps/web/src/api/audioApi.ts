// 音频 / MIDI 领域 API：生成、渲染、资源状态、下载 URL 与 blob 下载。

import { apiDownloadBlob, requestJson } from "./client";
import type {
  AssetsResponse,
  GenerateMidiResponse,
  RenderAudioResponse,
  StemExportResponse,
} from "./types";

export function generateMidi(songId: string): Promise<GenerateMidiResponse> {
  return requestJson(`/api/v1/songs/${songId}/midi/generate`, "POST");
}

export function renderAudio(songId: string): Promise<RenderAudioResponse> {
  return requestJson(`/api/v1/songs/${songId}/audio/render`, "POST");
}

export function getAssets(songId: string): Promise<AssetsResponse> {
  return requestJson(`/api/v1/songs/${songId}/assets`, "GET");
}

export function exportStems(songId: string): Promise<StemExportResponse> {
  return requestJson(`/api/v1/songs/${songId}/stems/export`, "POST");
}

export function getMidiDownloadUrl(songId: string): string {
  return `/api/v1/songs/${songId}/midi/download`;
}

export function getAudioStreamUrl(songId: string): string {
  return `/api/v1/songs/${songId}/audio/stream`;
}

export function getAudioDownloadUrl(songId: string): string {
  return `/api/v1/songs/${songId}/audio/download`;
}

export function getStemsZipUrl(songId: string): string {
  return `/api/v1/songs/${songId}/stems/download`;
}

export function downloadMidi(songId: string): Promise<Blob> {
  return apiDownloadBlob(getMidiDownloadUrl(songId));
}

export function downloadAudio(songId: string): Promise<Blob> {
  return apiDownloadBlob(getAudioDownloadUrl(songId));
}

export function downloadStems(songId: string): Promise<Blob> {
  return apiDownloadBlob(getStemsZipUrl(songId));
}
