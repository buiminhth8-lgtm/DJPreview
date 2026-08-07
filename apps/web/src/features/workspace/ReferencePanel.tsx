// 参考 MIDI 面板（复用既有 ReferenceMidiPanel）。

import type { GenerateFromReferenceResponse } from "../../api/types";
import ReferenceMidiPanelInner from "../midi/ReferenceMidiPanel";

export interface ReferencePanelProps {
  styleTemplateId: string | null;
  styleStrength: number;
  onGenerated: (result: GenerateFromReferenceResponse) => void;
  onError: (message: string) => void;
}

export default function ReferencePanel({
  styleTemplateId,
  styleStrength,
  onGenerated,
  onError,
}: ReferencePanelProps) {
  return (
    <section className="panel result">
      <h2>参考 MIDI 分析与生成</h2>
      <ReferenceMidiPanelInner
        styleTemplateId={styleTemplateId}
        styleStrength={styleStrength}
        onGenerated={onGenerated}
        onError={onError}
      />
    </section>
  );
}
