// MixerPanel：混音器（常驻，T38-G）。
// 无工程 / 无 tracks 时 Empty State；有 songId 时才挂载真实混音器（避免空请求）。

import type { AssetsResponse, MusicSpec } from "../../api/types";
import { EmptyState, SectionCard } from "../../components/ui";
import MixerPanelInner from "./MixerPanelInner";

export interface MixerPanelProps {
  songId?: string | null;
  musicSpec?: MusicSpec | null;
  refreshKey?: number;
  onApplied: (assets: AssetsResponse) => void;
  onError: (message: string) => void;
}

export function MixerPanel({
  songId,
  musicSpec,
  refreshKey = 0,
  onApplied,
  onError,
}: MixerPanelProps) {  const tracks = musicSpec?.tracks ?? [];
  const hasTracks = tracks.length > 0;

  let body;
  if (!songId) {
    body = (
      <EmptyState
        title="暂无可混音工程"
        description="请先生成 MusicSpec 或导入工程。"
      />
    );
  } else if (!hasTracks) {
    body = (
      <EmptyState
        title="暂无可混音轨道"
        description="生成 MusicSpec 后将显示轨道音量、声像、静音和独奏控制。"
      />
    );
  } else {
    body = <MixerPanelInner songId={songId} refreshKey={refreshKey} onApplied={onApplied} onError={onError} />;
  }

  return (
    <SectionCard title="混音器" description="音量 / 声像 / 静音 / 独奏">
      {body}
    </SectionCard>
  );
}

export default MixerPanel;
