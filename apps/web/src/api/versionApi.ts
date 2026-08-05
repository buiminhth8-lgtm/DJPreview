// 版本领域 API：列表、详情、diff、恢复。

import { requestJson } from "./client";
import type { RestoreVersionResponse, VersionDetailResponse, VersionDiffResponse, VersionsResponse } from "./types";

export function getVersions(songId: string): Promise<VersionsResponse> {
  return requestJson(`/api/v1/songs/${songId}/versions`, "GET");
}

export function getVersion(songId: string, versionId: string): Promise<VersionDetailResponse> {
  return requestJson(`/api/v1/songs/${songId}/versions/${versionId}`, "GET");
}

export function getVersionDiff(songId: string, versionId: string): Promise<VersionDiffResponse> {
  return requestJson(`/api/v1/songs/${songId}/versions/${versionId}/diff`, "GET");
}

export function restoreVersion(songId: string, versionId: string): Promise<RestoreVersionResponse> {
  return requestJson(`/api/v1/songs/${songId}/versions/${versionId}/restore`, "POST");
}
