import { useState } from "react";
import { exportProjectUrl, importProject } from "../api/musicApi";

interface ProjectIOPanelProps {
  songId: string;
  onImported: (songId: string) => void;
  onError: (message: string) => void;
}

export default function ProjectIOPanel({ songId, onImported, onError }: ProjectIOPanelProps) {
  const [busy, setBusy] = useState(false);

  const handleImport = async (file: File) => {
    setBusy(true);
    try {
      const result = await importProject(file);
      onImported(result.song_id);
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="project-io-panel">
      <div className="actions">
        <a className="download-link" href={exportProjectUrl(songId)} download>
          导出 .aimusic.zip
        </a>
      </div>
      <input
        type="file"
        accept=".zip"
        disabled={busy}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void handleImport(file);
        }}
      />
      <p className="muted-note">导入后会创建新的 song_id，不会覆盖现有项目。</p>
    </div>
  );
}
