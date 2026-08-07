// features/projects/projectTypes.ts（T33.2）
// 前端 Project 概念 == 后端 song project（/api/v1/songs/*）。
// 后端返回 snake_case，在 projectApi 边界映射为 camelCase，全项目一致。

export interface ProjectSummary {
  songId: string;
  title: string;
  createdAt: string | null;
  currentVersionId: string | null;
  hasMidi: boolean;
  hasAudio: boolean;
  hasStems: boolean;
  hasQualityReport: boolean;
  renderer: string | null;
  soundfontName: string | null;
}

export interface ProjectListResponse {
  projects: ProjectSummary[];
  total: number;
}

export interface ProjectDetail {
  songId: string;
  title: string;
  musicSpec: unknown;
  currentVersionId?: string | null;
}

export interface ImportProjectResult {
  songId: string;
  imported: boolean;
  summary: Record<string, unknown>;
  sourceSongId?: string | null;
  currentVersionId?: string | null;
  versionCount: number;
  warnings: string[];
}

export interface DeleteProjectResult {
  songId: string;
  deleted: boolean;
}

export interface ExportProjectResult {
  blob: Blob;
  filename: string;
}
