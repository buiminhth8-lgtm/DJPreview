// 播放 / 资产面板：MIDI / WAV / stems。

import type { AudioMetadata, GenerateMidiResponse, RenderAudioResponse } from "../../api/types";
import AudioPlayer from "../AudioPlayer";
import StemExportPanel from "../StemExportPanel";

export interface PlayerPanelProps {
  songId: string;
  midiResult: GenerateMidiResponse | null;
  audioResult: RenderAudioResponse | null;
  audioStreamUrl: string | null;
  midiDownloadUrl: string | null;
  audioDownloadUrl: string | null;
  loadingMidi: boolean;
  loadingAudio: boolean;
  onGenerateMidi: () => void;
  onRenderAudio: () => void;
  onError: (message: string) => void;
}

export default function PlayerPanel({
  songId,
  midiResult,
  audioResult,
  audioStreamUrl,
  midiDownloadUrl,
  audioDownloadUrl,
  loadingMidi,
  loadingAudio,
  onGenerateMidi,
  onRenderAudio,
  onError,
}: PlayerPanelProps) {
  return (
    <section className="panel result">
      <h2>播放与下载</h2>
      <p className="song-id">
        song_id：<code>{songId}</code>
      </p>
      <div className="midi-actions">
        <button onClick={onGenerateMidi} disabled={loadingMidi}>
          {loadingMidi ? "MIDI 生成中…" : "生成 MIDI"}
        </button>
        {midiDownloadUrl && (
          <a className="download-link" href={midiDownloadUrl} download={`${songId}.mid`}>
            下载 MIDI
          </a>
        )}
      </div>
      {midiResult && (
        <div className="summary">
          <div className="summary-row">
            <span className="summary-label">轨道数</span>
            <span className="summary-value">{midiResult.summary.tracks}</span>
          </div>
          <div className="summary-row">
            <span className="summary-label">小节数</span>
            <span className="summary-value">{midiResult.summary.bars}</span>
          </div>
          <div className="summary-row">
            <span className="summary-label">BPM</span>
            <span className="summary-value">{midiResult.summary.bpm}</span>
          </div>
        </div>
      )}
      <div className="midi-actions">
        <button onClick={onRenderAudio} disabled={loadingAudio}>
          {loadingAudio ? "WAV 渲染中…" : "渲染 WAV"}
        </button>
      </div>
      {audioResult && audioStreamUrl && (
        <>
          <AudioPlayer audioUrl={audioStreamUrl} downloadUrl={audioDownloadUrl ?? ""} />
          <AudioMeta metadata={audioResult.metadata} />
        </>
      )}
      <details className="panel result">
        <summary>
          <h2>分轨导出</h2>
        </summary>
        <StemExportPanel songId={songId} onError={onError} />
      </details>
    </section>
  );
}

function AudioMeta({ metadata }: { metadata: AudioMetadata }) {
  const rows: Array<[string, string]> = [
    ["渲染器", metadata.renderer],
    ["采样率", `${metadata.sample_rate} Hz`],
    [
      "时长",
      metadata.duration_seconds != null ? `${metadata.duration_seconds.toFixed(2)} s` : "未知",
    ],
    ["文件大小", `${(metadata.file_size / 1024).toFixed(1)} KB`],
  ];
  return (
    <div className="summary audio-meta">
      {rows.map(([label, value]) => (
        <div className="summary-row" key={label}>
          <span className="summary-label">{label}</span>
          <span className="summary-value">{value}</span>
        </div>
      ))}
      {metadata.warnings.length > 0 && (
        <div className="warnings">提示：{metadata.warnings.join("；")}</div>
      )}
    </div>
  );
}
