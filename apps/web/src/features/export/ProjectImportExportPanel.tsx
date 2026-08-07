// ProjectImportExportPanel：工程导入导出（常驻，T38-H）。
// 导入 .aimusic.zip 始终可用；导出工程 / 下载 MIDI / WAV / Stems 无资产时 disabled。

import { useState } from "react";
import { importProject } from "../projects/projectApi";
import { ActionButton, ButtonRow, EmptyState, InlineNotice, SectionCard } from "../../components/ui";
import { ExportMenu } from "./ExportMenu";

export interface ProjectImportExportPanelProps {
  songId?: string | null;
  projectTitle?: string | null;
  hasMidi?: boolean;
  hasAudio?: boolean;
  hasStems?: boolean;
  onImported?: (songId: string) => void;
  onExportStems?: () => void;
  onDeleteProject?: () => void;
  onError?: (message: string) => void;
}

export function ProjectImportExportPanel({
  songId,
  projectTitle,
  hasMidi = false,
  hasAudio = false,
  hasStems = false,
  onImported,
  onExportStems,
  onDeleteProject,
  onError,
}: ProjectImportExportPanelProps) {
  const [busy, setBusy] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const hasSong = Boolean(songId);

  const handleImport = async (file: File) => {
    if (!file) return;
    setBusy(true);
    setImportError(null);
    setFileName(file.name);
    try {
      const result = await importProject(file);
      onImported?.(result.songId);
    } catch (e) {
      setImportError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  let body;
  if (!hasSong) {
    body = (
      <EmptyState
        title="可以导入 .aimusic.zip 工程"
        description="生成或导入工程后，可导出当前工程、MIDI、WAV 和分轨。"
      />
    );
  } else {
    body = (
      <div className="workspace-import-export">
        <p className="workspace-import-export__ready">当前工程可导出：可导出 .aimusic.zip 工程包，并下载已生成的 MIDI / WAV / Stems。</p>
      </div>
    );
  }

  return (
    <SectionCard title="工程导入导出" description=".aimusic.zip 导入 / 导出">
      {/* 导入始终可用 */}
      <div className="workspace-import-export">
        <label className="workspace-import-export__file">
          <input
            type="file"
            accept=".aimusic.zip,.zip"
            disabled={busy}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void handleImport(file);
              e.target.value = "";
            }}
          />
          {fileName && <span className="workspace-import-export__filename">{fileName}</span>}
        </label>
        {busy && <div className="ui-loading-state"><span className="ui-loading-state__spinner" /> 正在导入工程…</div>}
        {importError && <InlineNotice variant="danger" title="导入失败">{importError}</InlineNotice>}

        <ButtonRow className="workspace-import-export__actions">
          <ActionButton
            variant="danger"
            onClick={onDeleteProject}
            disabled={!hasSong}
            disabledReason={!hasSong ? "请先生成或导入工程" : undefined}
          >
            删除当前工程
          </ActionButton>
        </ButtonRow>
      </div>
      {body}
      {hasSong && (
        <ExportMenu
          songId={songId}
          projectTitle={projectTitle}
          hasMidi={hasMidi}
          hasAudio={hasAudio}
          hasStems={hasStems}
          onStemsExported={onExportStems}
          onError={onError}
        />
      )}
      <p className="muted-note">导入后会创建新的 song_id，不会覆盖现有项目。</p>
    </SectionCard>
  );
}

export default ProjectImportExportPanel;
