// 歌曲领域 API：生成、读取、编辑、重生成。

import { requestJson } from "./client";
import type {
  EditSongResponse,
  GenerateSongResponse,
  MusicSpec,
  RegenerationRequest,
  RegenerationResult,
} from "./types";

export function generateMusicSpec(
  prompt: string,
  styleTemplateId?: string | null,
  styleStrength = 0.7,
): Promise<GenerateSongResponse> {
  return requestJson("/api/v1/songs/generate", "POST", {
    prompt,
    ...(styleTemplateId ? { style_template_id: styleTemplateId, style_strength: styleStrength } : {}),
  });
}

export function getSong(songId: string): Promise<{ song_id: string; music_spec: MusicSpec }> {
  return requestJson(`/api/v1/songs/${songId}`, "GET");
}

export function editSong(
  songId: string,
  instruction: string,
  autoRender = true,
): Promise<EditSongResponse> {
  return requestJson(`/api/v1/songs/${songId}/edit`, "POST", {
    instruction,
    auto_render: autoRender,
  });
}

export function regenerateSong(songId: string, request: RegenerationRequest): Promise<RegenerationResult> {
  return requestJson(`/api/v1/songs/${songId}/regenerate`, "POST", request);
}
