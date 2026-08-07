// ExportMenu：工程导出统一入口（T33.8）。
// 导出 MIDI / WAV / Stems / .aimusic.zip；无对应资产时禁用，避免点击后才 404。
// 统一走 downloadBlob（createObjectURL → click → revokeObjectURL）；文件名优先后端
// Content-Disposition，否则用安全化的 {title}.ext fallback。

import { useState } from "react";
import { ActionButton, ButtonRow } from "../../components/ui";
import {
  downloadMidiAsset,
  downloadProjectBundle,
  downloadStemsAsset,
  downloadWavAsset,
} from "./downloadActions";

export interface ExportMenuProps {
  songId?: string | null;
  projectTitle?: string | null;
  hasMidi?: boolean;
  hasAudio?: boolean;
  hasStems?: boolean;
  onStemsExported?: () => void;
  onError?: (message: string) => void;
}

export function ExportMenu({
  songId,
  projectTitle,
  hasMidi = false,
  hasAudio = false,
  hasStems = false,
  onStemsExported,
  onError,
}: ExportMenuProps) {
  const [downloading, setDownloading] = useState<string | null>(null);
  const hasSong = Boolean(songId);

  const handleDownload = async (kind: "midi" | "wav" | "stems" | "project") => {
    if (!songId || downloading) return;
    setDownloading(kind);
    try {
      if (kind === "midi") {
        await downloadMidiAsset(songId, projectTitle);
      } else if (kind === "wav") {
        await downloadWavAsset(songId, projectTitle);
      } else if (kind === "stems") {
        await downloadStemsAsset(songId, projectTitle);
        onStemsExported?.();
      } else {
        await downloadProjectBundle(songId);
      }
    } catch (e) {
      onError?.(e instanceof Error ? e.message : String(e));
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="export-menu">
      <ButtonRow className="workspace-import-export__actions">
        <ActionButton
          variant="primary"
          onClick={() => void handleDownload("project")}
          disabled={!hasSong || downloading !== null}
          loading={downloading === "project"}
          disabledReason={!hasSong ? "请先生成或导入工程" : undefined}
        >
          {downloading === "project" ? "导出中…" : "导出工程"}
        </ActionButton>
        <ActionButton
          variant="ghost"
          onClick={() => void handleDownload("midi")}
          disabled={!hasMidi || downloading !== null}
          loading={downloading === "midi"}
          disabledReason={!hasMidi ? "当前工程暂无 MIDI" : undefined}
        >
          {downloading === "midi" ? "下载中…" : "下载 MIDI"}
        </ActionButton>
        <ActionButton
          variant="ghost"
          onClick={() => void handleDownload("wav")}
          disabled={!hasAudio || downloading !== null}
          loading={downloading === "wav"}
          disabledReason={!hasAudio ? "当前工程暂无 WAV 音频" : undefined}
        >
          {downloading === "wav" ? "下载中…" : "下载 WAV"}
        </ActionButton>
        <ActionButton
          variant="ghost"
          onClick={() => void handleDownload("stems")}
          disabled={!hasSong || !hasStems || downloading !== null}
          loading={downloading === "stems"}
          disabledReason={!hasStems ? "请先生成 MIDI 并渲染 WAV" : undefined}
        >
          {downloading === "stems" ? "导出中…" : "导出 Stems"}
        </ActionButton>
      </ButtonRow>
    </div>
  );
}

export default ExportMenu;
