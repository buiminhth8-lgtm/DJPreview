// 混音领域 API：读取、更新、应用。

import { requestJson } from "./client";
import type { ApplyMixResponse, AssetsResponse, MixResponse, MixSpec, TrackMixPatch } from "./types";

export function getMix(songId: string): Promise<MixResponse> {
  return requestJson(`/api/v1/songs/${songId}/mix`, "GET");
}

export function updateMix(
  songId: string,
  patch: { master_volume?: number; tracks: TrackMixPatch[] },
  apply: boolean,
): Promise<{ song_id: string; version_id: string | null; mix_spec: MixSpec; assets: AssetsResponse | null }> {
  return requestJson(`/api/v1/songs/${songId}/mix?apply=${apply}`, "PATCH", patch);
}

export function applyMix(songId: string): Promise<ApplyMixResponse> {
  return requestJson(`/api/v1/songs/${songId}/mix/apply`, "POST");
}
