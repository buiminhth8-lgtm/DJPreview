// 导出下载动作（T33.8）：MIDI / WAV / Stems / 工程导出统一走 downloadBlob。

import { downloadAudio, downloadMidi, downloadStems } from "../../api/audioApi";
import { exportProject } from "../projects/projectApi";
import { downloadBlob } from "../../shared/utils/download";

export function safeFilename(title: string | null | undefined, ext: string): string {
  const base = (title ?? "project").trim().replace(/[\\/:*?"<>|]+/g, "_").replace(/\s+/g, "_") || "project";
  return `${base}.${ext}`;
}

export async function downloadMidiAsset(
  songId: string,
  title?: string | null,
): Promise<void> {
  const blob = await downloadMidi(songId);
  downloadBlob(blob, safeFilename(title, "mid"));
}

export async function downloadWavAsset(
  songId: string,
  title?: string | null,
): Promise<void> {
  const blob = await downloadAudio(songId);
  downloadBlob(blob, safeFilename(title, "wav"));
}

export async function downloadStemsAsset(
  songId: string,
  title?: string | null,
): Promise<void> {
  const blob = await downloadStems(songId);
  downloadBlob(blob, safeFilename(title, "stems.zip"));
}

export async function downloadProjectBundle(
  songId: string,
): Promise<void> {
  const result = await exportProject(songId);
  downloadBlob(result.blob, result.filename);
}
