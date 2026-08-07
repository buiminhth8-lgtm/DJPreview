// features/generation/generationTypes.ts（T33.4）
// 生成流程最小类型（基于真实 GenerateSongResponse / MusicSpec）。

import type { MusicSpec, WarningItem } from "../../api/types";

export interface GenerateSongInput {
  prompt: string;
  styleTemplateId?: string | null;
  styleStrength?: number;
}

export interface GeneratedProjectSummary {
  songId: string;
  title: string;
  musicSpec: MusicSpec;
  hasMidi: boolean;
  hasAudio: boolean;
  warnings: WarningItem[];
  requestId?: string | null;
}
