// features/projects/projectApi.ts（T33.2）
// 工程生命周期统一入口：列表 / 详情 / 删除 / 导入 / 导出。
// 数据流：页面 → hook → projectApi → client.ts(httpClient) → backend。
// 后端 URL 仍为 /api/v1/songs（前端 Project == 后端 song project），此处只做前端映射。

import { apiDownloadBlob, API_BASE_URL, ApiRequestError, requestJson } from "../../api/client";
import { filenameFromContentDisposition } from "../../shared/utils/download";
import type {
  DeleteProjectResult,
  ExportProjectResult,
  ImportProjectResult,
  ProjectDetail,
  ProjectSummary,
} from "./projectTypes";

const PROJECTS_BASE = "/api/v1";

interface ListProjectsRaw {
  projects: RawProjectSummary[];
  total: number;
}

interface RawProjectSummary {
  song_id: string;
  title?: string | null;
  created_at?: string | null;
  current_version_id?: string | null;
  has_midi?: boolean;
  has_audio?: boolean;
  has_stems?: boolean;
  has_quality_report?: boolean;
  renderer?: string | null;
  soundfont_name?: string | null;
}

interface GetSongRaw {
  song_id: string;
  music_spec: unknown;
}

interface ImportProjectRaw {
  song_id: string;
  imported: boolean;
  summary: Record<string, unknown>;
  source_song_id?: string | null;
  current_version_id?: string | null;
  version_count?: number;
  warnings?: string[];
}

function mapSummary(raw: RawProjectSummary): ProjectSummary {
  return {
    songId: raw.song_id,
    title: raw.title || "未命名工程",
    createdAt: raw.created_at ?? null,
    currentVersionId: raw.current_version_id ?? null,
    hasMidi: Boolean(raw.has_midi),
    hasAudio: Boolean(raw.has_audio),
    hasStems: Boolean(raw.has_stems),
    hasQualityReport: Boolean(raw.has_quality_report),
    renderer: raw.renderer ?? null,
    soundfontName: raw.soundfont_name ?? null,
  };
}

export function assertSongId(songId: string | undefined | null): asserts songId is string {
  if (!songId || !songId.trim()) {
    throw new ApiRequestError("缺少工程 ID（songId）", { status: 400, code: "INVALID_SONG_ID" });
  }
}

export async function listProjects(options?: { signal?: AbortSignal }): Promise<ProjectSummary[]> {
  const data = await requestJson<Partial<ListProjectsRaw>>(`${PROJECTS_BASE}/projects`, "GET", undefined, options?.signal);
  const raw = data.projects ?? [];
  return raw.map(mapSummary);
}

export async function getProject(
  songId: string | undefined | null,
  options?: { signal?: AbortSignal },
): Promise<ProjectDetail> {
  assertSongId(songId);
  const encoded = encodeURIComponent(songId);
  const data = await requestJson<GetSongRaw>(`${PROJECTS_BASE}/songs/${encoded}`, "GET", undefined, options?.signal);
  const title =
    typeof data.music_spec === "object" &&
    data.music_spec !== null &&
    "title" in data.music_spec &&
    typeof (data.music_spec as Record<string, unknown>).title === "string"
      ? ((data.music_spec as Record<string, unknown>).title as string)
      : "未命名工程";
  return {
    songId: data.song_id,
    title,
    musicSpec: data.music_spec,
  };
}

export async function deleteProject(songId: string): Promise<DeleteProjectResult> {
  assertSongId(songId);
  const encoded = encodeURIComponent(songId);
  const data = await requestJson<{ song_id: string; deleted: boolean }>(
    `${PROJECTS_BASE}/songs/${encoded}`,
    "DELETE",
  );
  return { songId: data.song_id, deleted: Boolean(data.deleted) };
}

export async function importProject(
  file: File,
  options?: { signal?: AbortSignal },
): Promise<ImportProjectResult> {
  const form = new FormData();
  form.append("file", file);
  const data = await requestJson<ImportProjectRaw>(
    `${PROJECTS_BASE}/projects/import`,
    "POST",
    form,
    options?.signal,
  );
  return {
    songId: data.song_id,
    imported: Boolean(data.imported),
    summary: data.summary ?? {},
    sourceSongId: data.source_song_id ?? null,
    currentVersionId: data.current_version_id ?? null,
    versionCount: data.version_count ?? 0,
    warnings: data.warnings ?? [],
  };
}

export async function exportProject(
  songId: string,
  options?: { signal?: AbortSignal },
): Promise<ExportProjectResult> {
  assertSongId(songId);
  const encoded = encodeURIComponent(songId);
  const url = `${PROJECTS_BASE}/songs/${encoded}/project/export`;
  const blob = await apiDownloadBlob(url, options?.signal);
  const fallback = `${songId}.aimusic.zip`;
  const header = await fetch(`${API_BASE_URL}${url}`, { signal: options?.signal })
    .then((r) => r.headers.get("Content-Disposition"))
    .catch(() => null);
  return {
    blob,
    filename: filenameFromContentDisposition(header, fallback),
  };
}
