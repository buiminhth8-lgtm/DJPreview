// 混音器面板（复用既有 MixerPanel）。

import type { AssetsResponse } from "../../api/types";
import MixerPanelInner from "../MixerPanel";

export interface MixerPanelProps {
  songId: string;
  refreshKey: number;
  onApplied: (assets: AssetsResponse) => void;
  onError: (message: string) => void;
}

export default function MixerPanel({ songId, refreshKey, onApplied, onError }: MixerPanelProps) {
  return (
    <section className="panel result">
      <h2>混音器</h2>
      <MixerPanelInner songId={songId} refreshKey={refreshKey} onApplied={onApplied} onError={onError} />
    </section>
  );
}
