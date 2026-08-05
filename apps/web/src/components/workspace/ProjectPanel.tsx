// 工程导入导出面板（复用既有 ProjectIOPanel）。

import ProjectIOPanelInner from "../ProjectIOPanel";

export interface ProjectPanelProps {
  songId: string;
  onImported: (songId: string) => void;
  onError: (message: string) => void;
}

export default function ProjectPanel({ songId, onImported, onError }: ProjectPanelProps) {
  return (
    <section className="panel result">
      <h2>工程导入导出</h2>
      <ProjectIOPanelInner songId={songId} onImported={onImported} onError={onError} />
    </section>
  );
}
