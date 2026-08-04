import { useState } from "react";
import { exportStems, resolveUrl, type StemExportResponse } from "../api/musicApi";

interface StemExportPanelProps {
  songId: string;
  onError: (message: string) => void;
}

export default function StemExportPanel({ songId, onError }: StemExportPanelProps) {
  const [result, setResult] = useState<StemExportResponse | null>(null);
  const [busy, setBusy] = useState(false);

  const handleExport = async () => {
    setBusy(true);
    try {
      const res = await exportStems(songId);
      setResult(res);
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="stem-panel">
      <div className="actions">
        <button onClick={handleExport} disabled={busy}>
          {busy ? "导出中…" : "导出分轨"}
        </button>
      </div>
      {result && (
        <div className="stem-result">
          {result.stems.length > 0 && (
            <table className="track-table">
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
            <div className="warnings">提示：{result.warnings.join("；")}</div>
          )}
        </div>
      )}
    </div>
  );
}
