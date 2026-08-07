// StemsPanel：Stems / 分轨导出（常驻，T38-G）。
// 无工程 / 无 MIDI / 无 WAV 时 Empty State + 导出按钮 disabled 并显示原因；
// 有 songId 时复用真实 StemExportPanel（内部处理导出）。

import { useState } from "react";
import { exportStems } from "../../api/audioApi";
import { resolveUrl } from "../../api/client";
import type { StemExportResponse } from "../../api/types";
import { ActionButton, ButtonRow, EmptyState, SectionCard, StatusBadge } from "../../components/ui";

export interface StemsPanelProps {
  songId?: string | null;
  hasMidi?: boolean;
  hasAudio?: boolean;
  onError?: (message: string) => void;
}

export function StemsPanel({ songId, hasMidi = false, hasAudio = false, onError }: StemsPanelProps) {
  const [result, setResult] = useState<StemExportResponse | null>(null);
  const [busy, setBusy] = useState(false);

  const handleExport = async () => {
    if (!songId) return;
    setBusy(true);
    try {
      const res = await exportStems(songId);
      setResult(res);
    } catch (e) {
      onError?.(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const disabledReason = !songId
    ? "请先生成或导入工程"
    : !hasMidi
      ? "请先生成 MIDI"
      : !hasAudio
        ? "请先渲染 WAV"
        : busy
          ? "正在导出分轨"
          : undefined;

  let body;
  if (!songId) {
    body = (
      <EmptyState title="暂无分轨工程" description="请先生成或导入工程。" />
    );
  } else if (!hasMidi) {
    body = (
      <EmptyState
        title="暂无分轨"
        description="生成 MIDI 并渲染 WAV 后可导出分轨。"
        action={
          <ButtonRow>
            <ActionButton variant="secondary" onClick={() => void handleExport()} disabled={!hasMidi} disabledReason="请先生成 MIDI">
              导出 Stems
            </ActionButton>
          </ButtonRow>
        }
      />
    );
  } else {
    body = (
      <div className="workspace-stems">
        <ButtonRow className="workspace-stems__actions">
          <ActionButton variant="primary" onClick={() => void handleExport()} disabled={Boolean(disabledReason)} disabledReason={disabledReason} loading={busy}>
            {busy ? "导出中…" : "导出 Stems"}
          </ActionButton>
        </ButtonRow>
        {!hasAudio && (
          <p className="workspace-stems__hint">提示：当前无 WAV，导出将基于 MIDI 生成分轨。</p>
        )}
        {result && (
          <div className="workspace-stems__result">
            {result.stems.length > 0 && (
              <table className="workspace-track-table">
                <thead>
                  <tr>
                    <th>track</th>
                    <th>MIDI</th>
                    <th>WAV</th>
                  </tr>
                </thead>
                <tbody>
                  {result.stems.map((stem) => (
                    <tr key={stem.track_id}>
                      <td>{stem.track_id}</td>
                      <td>
                        <a className="download-link" href={resolveUrl(stem.midi_download_url)} download>
                          下载 MIDI
                        </a>
                      </td>
                      <td>
                        <a className="download-link" href={resolveUrl(stem.wav_download_url)} download>
                          下载 WAV
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <p>
              <a className="download-link" href={resolveUrl(result.zip_download_url)} download>
                下载 stems.zip
              </a>
            </p>
            {result.warnings.length > 0 && (
              <div className="workspace-stems__warnings">提示：{result.warnings.join("；")}</div>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <SectionCard
      title="Stems / 分轨导出"
      description="各轨道独立 MIDI / WAV"
      badge={hasAudio ? <StatusBadge variant="success">assets ready</StatusBadge> : <StatusBadge variant="neutral">No assets</StatusBadge>}
    >
      {body}
    </SectionCard>
  );
}
