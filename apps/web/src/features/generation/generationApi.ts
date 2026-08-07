// features/generation/generationApi.ts（T33.4）
// 生成 API 边界：复用现有 songApi.generateMusicSpec，把响应规范化为
// GeneratedProjectSummary，避免页面到处判断 snake_case 字段。

import { generateMusicSpec } from "../../api/songApi";
import type { GenerateSongInput, GeneratedProjectSummary } from "./generationTypes";

export async function generateSong(
  input: GenerateSongInput,
  options?: { signal?: AbortSignal },
): Promise<GeneratedProjectSummary> {
  const response = await generateMusicSpec(
    input.prompt,
    input.styleTemplateId || null,
    input.styleStrength ?? 0.7,
    options?.signal,
  );
  return {
    songId: response.song_id,
    title: response.music_spec.title || "未命名工程",
    musicSpec: response.music_spec,
    hasMidi: false,
    hasAudio: false,
    warnings: response.warnings ?? [],
    requestId: response.request_id ?? null,
  };
}
