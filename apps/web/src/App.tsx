import { useState } from "react";
import {
  generateMidi,
  generateMusicSpec,
  renderAudio,
  resolveUrl,
  type AudioMetadata,
  type GenerateMidiResponse,
  type MusicSpec,
  type RenderAudioResponse,
} from "./api/musicApi";
import AudioPlayer from "./components/AudioPlayer";
import MusicSummary from "./components/MusicSummary";
import SectionTimeline from "./components/SectionTimeline";
import TrackList from "./components/TrackList";

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [loadingSpec, setLoadingSpec] = useState(false);
  const [loadingMidi, setLoadingMidi] = useState(false);
  const [loadingAudio, setLoadingAudio] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [songId, setSongId] = useState<string | null>(null);
  const [musicSpec, setMusicSpec] = useState<MusicSpec | null>(null);
  const [midiResult, setMidiResult] = useState<GenerateMidiResponse | null>(null);
  const [audioResult, setAudioResult] = useState<RenderAudioResponse | null>(null);
  const [audioStreamUrl, setAudioStreamUrl] = useState<string | null>(null);

  const handleGenerateSpec = async () => {
    if (!prompt.trim()) {
      setError("请输入音乐描述");
      return;
    }
    setLoadingSpec(true);
    setError(null);
    setMidiResult(null);
    setAudioResult(null);
    setAudioStreamUrl(null);
    try {
      const result = await generateMusicSpec(prompt.trim());
      setSongId(result.song_id);
      setMusicSpec(result.music_spec);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingSpec(false);
    }
  };

  const handleGenerateMidi = async () => {
    if (!songId) return;
    setLoadingMidi(true);
    setError(null);
    setAudioResult(null);
    setAudioStreamUrl(null);
    try {
      const result = await generateMidi(songId);
      setMidiResult(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingMidi(false);
    }
  };

  const handleRenderAudio = async () => {
    if (!songId) return;
    setLoadingAudio(true);
    setError(null);
    try {
      const result = await renderAudio(songId);
      setAudioResult(result);
      // 加时间戳防止浏览器缓存旧音频
      setAudioStreamUrl(`${resolveUrl(result.stream_url)}?t=${Date.now()}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingAudio(false);
    }
  };

  const midiDownloadUrl = midiResult ? resolveUrl(midiResult.download_url) : null;

  return (
    <div className="container">
      <header>
        <h1>AI Music MVP</h1>
        <p className="subtitle">一句话生成 MusicSpec → MIDI → 试听 WAV</p>
      </header>

      <section className="panel">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="例如：生成一段忧郁空灵的钢琴配乐，72 BPM，D 小调"
          rows={4}
          disabled={loadingSpec}
        />
        <div className="actions">
          <button onClick={handleGenerateSpec} disabled={loadingSpec}>
            {loadingSpec ? "生成中…" : "生成 MusicSpec"}
          </button>
        </div>
      </section>

      {error && <div className="error">⚠ {error}</div>}

      {musicSpec && songId && (
        <>
          <section className="panel result">
            <h2>MusicSpec 摘要</h2>
            <p className="song-id">
              song_id：<code>{songId}</code>
            </p>
            <MusicSummary spec={musicSpec} />

            <h3>段落结构</h3>
            <SectionTimeline sections={musicSpec.form} />

            <h3>轨道列表</h3>
            <TrackList tracks={musicSpec.tracks} />

            <div className="midi-actions">
              <button onClick={handleGenerateMidi} disabled={loadingMidi}>
                {loadingMidi ? "MIDI 生成中…" : "生成 MIDI"}
              </button>
              {midiDownloadUrl && (
                <a className="download-link" href={midiDownloadUrl} download={`${songId}.mid`}>
                  下载 MIDI
                </a>
              )}
            </div>
          </section>

          {midiResult && (
            <section className="panel result">
              <h2>MIDI 已生成</h2>
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
              <div className="midi-actions">
                <button onClick={handleRenderAudio} disabled={loadingAudio}>
                  {loadingAudio ? "WAV 渲染中…" : "渲染 WAV"}
                </button>
              </div>
            </section>
          )}

          {audioResult && audioStreamUrl && (
            <section className="panel result">
              <h2>音频试听</h2>
              <AudioPlayer
                audioUrl={audioStreamUrl}
                downloadUrl={resolveUrl(audioResult.download_url)}
              />
              <AudioMeta metadata={audioResult.metadata} />
            </section>
          )}
        </>
      )}
    </div>
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
