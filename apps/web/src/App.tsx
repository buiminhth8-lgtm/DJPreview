import { useState } from "react";
import {
  editSong,
  generateMidi,
  generateMusicSpec,
  getVersions,
  renderAudio,
  resolveUrl,
  restoreVersion,
  type AudioMetadata,
  type DiffItem,
  type EditSongResponse,
  type GenerateMidiResponse,
  type MusicSpec,
  type OptimizeResponse,
  type RenderAudioResponse,
  type VersionInfo,
} from "./api/musicApi";
import ArrangementInspector from "./components/ArrangementInspector";
import AudioPlayer from "./components/AudioPlayer";
import MixerPanel from "./components/MixerPanel";
import StemExportPanel from "./components/StemExportPanel";

function audioResultFromAssets(
  songId: string,
  assets: EditSongResponse["assets"],
): RenderAudioResponse | null {
  if (!assets.audio) return null;
  return {
    song_id: songId,
    audio_file: "output.wav",
    stream_url: assets.audio.stream_url,
    download_url: assets.audio.download_url,
    metadata: assets.audio.metadata ?? {
      audio_file: "output.wav",
      renderer: "unknown",
      sample_rate: 0,
      duration_seconds: null,
      file_size: 0,
      generated_at: null,
      generator_version: null,
      warnings: [],
    },
  };
}

function formatDiff(diff: DiffItem[]): string {
  return diff
    .map((d) => {
      const oldV = typeof d.old === "object" ? JSON.stringify(d.old) : String(d.old ?? "—");
      const newV = typeof d.new === "object" ? JSON.stringify(d.new) : String(d.new ?? "—");
      return `${d.field}: ${oldV} → ${newV}`;
    })
    .join("\n");
}

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [loadingSpec, setLoadingSpec] = useState(false);
  const [loadingMidi, setLoadingMidi] = useState(false);
  const [loadingAudio, setLoadingAudio] = useState(false);
  const [loadingEdit, setLoadingEdit] = useState(false);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [songId, setSongId] = useState<string | null>(null);
  const [musicSpec, setMusicSpec] = useState<MusicSpec | null>(null);
  const [midiResult, setMidiResult] = useState<GenerateMidiResponse | null>(null);
  const [audioResult, setAudioResult] = useState<RenderAudioResponse | null>(null);
  const [audioStreamUrl, setAudioStreamUrl] = useState<string | null>(null);

  const [editPrompt, setEditPrompt] = useState("");
  const [lastDiff, setLastDiff] = useState<DiffItem[] | null>(null);
  const [versions, setVersions] = useState<VersionInfo[] | null>(null);
  const [currentVersionId, setCurrentVersionId] = useState<string | null>(null);
  const [pianoRefreshKey, setPianoRefreshKey] = useState(0);

  const refreshAudioFromAssets = (songId: string, assets: EditSongResponse["assets"]) => {
    const next = audioResultFromAssets(songId, assets);
    setAudioResult(next);
    if (next) {
      setAudioStreamUrl(`${resolveUrl(next.stream_url)}?t=${Date.now()}`);
    } else {
      setAudioStreamUrl(null);
    }
  };

  const refreshVersions = async () => {
    if (!songId) return;
    const result = await getVersions(songId);
    setVersions(result.versions);
    setCurrentVersionId(result.current_version_id);
  };

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
    setVersions(null);
    setLastDiff(null);
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
      setAudioStreamUrl(`${resolveUrl(result.stream_url)}?t=${Date.now()}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingAudio(false);
    }
  };

  const handleApplyEdit = async () => {
    if (!songId || !editPrompt.trim()) {
      setError("请输入修改指令");
      return;
    }
    setLoadingEdit(true);
    setError(null);
    try {
      const result = await editSong(songId, editPrompt.trim());
      setMusicSpec(result.music_spec);
      setLastDiff(result.diff);
      refreshAudioFromAssets(songId, result.assets);
      await refreshVersions();
      setPianoRefreshKey((k) => k + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingEdit(false);
    }
  };

  const handleLoadVersions = async () => {
    if (!songId) return;
    setLoadingVersions(true);
    setError(null);
    try {
      await refreshVersions();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingVersions(false);
    }
  };

  const handleRestore = async (versionId: string) => {
    if (!songId) return;
    setError(null);
    try {
      const result = await restoreVersion(songId, versionId);
      setMusicSpec(result.music_spec);
      refreshAudioFromAssets(songId, result.assets);
      await refreshVersions();
      setPianoRefreshKey((k) => k + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleMixApplied = (assets: EditSongResponse["assets"]) => {
    refreshAudioFromAssets(songId ?? "", assets);
    setPianoRefreshKey((k) => k + 1);
  };

  const handleOptimized = async (result: OptimizeResponse) => {
    setMusicSpec(result.music_spec);
    refreshAudioFromAssets(result.song_id, result.assets);
    await refreshVersions();
    setPianoRefreshKey((k) => k + 1);
  };

  const midiDownloadUrl = midiResult ? resolveUrl(midiResult.download_url) : null;

  return (
    <div className="container">
      <header>
        <h1>AI Music MVP</h1>
        <p className="subtitle">
          生成 MusicSpec → MIDI → WAV → 修改/版本 → 混音/可视化/质量/导出
        </p>
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
            <h2>播放与下载</h2>
            <p className="song-id">
              song_id：<code>{songId}</code>
            </p>
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
              <button onClick={handleRenderAudio} disabled={loadingAudio}>
                {loadingAudio ? "WAV 渲染中…" : "渲染 WAV"}
              </button>
            </div>
            {audioResult && audioStreamUrl && (
              <>
                <AudioPlayer
                  audioUrl={audioStreamUrl}
                  downloadUrl={resolveUrl(audioResult.download_url)}
                />
                <AudioMeta metadata={audioResult.metadata} />
              </>
            )}
          </section>

          <details className="panel result" open>
            <summary>
              <h2>编曲检查（摘要 / 段落 / 轨道 / 钢琴卷帘 / 质量）</h2>
            </summary>
            <ArrangementInspector
              songId={songId}
              spec={musicSpec}
              refreshKey={pianoRefreshKey}
              onOptimized={handleOptimized}
              onError={(msg) => setError(msg)}
            />
          </details>

          <details className="panel result">
            <summary>
              <h2>自然语言修改与版本管理</h2>
            </summary>
            <textarea
              value={editPrompt}
              onChange={(e) => setEditPrompt(e.target.value)}
              placeholder="例如：副歌更亮一点 / 整首更快一点 / 加点中国风 / 去掉贝斯 / 副歌加鼓"
              rows={3}
              disabled={loadingEdit}
            />
            <div className="actions">
              <button onClick={handleApplyEdit} disabled={loadingEdit}>
                {loadingEdit ? "修改中…" : "应用修改"}
              </button>
            </div>
            {lastDiff && lastDiff.length > 0 && (
              <div className="diff-box">
                <h3>修改内容</h3>
                <pre>{formatDiff(lastDiff)}</pre>
              </div>
            )}
            {lastDiff && lastDiff.length === 0 && (
              <p className="muted-note">本次修改未产生字段变化。</p>
            )}
            <div className="actions">
              <button onClick={handleLoadVersions} disabled={loadingVersions}>
                {loadingVersions ? "加载中…" : "查看版本"}
              </button>
            </div>
            {versions && (
              <div className="version-list">
                {[...versions].reverse().map((v) => (
                  <div
                    className={`version-item${v.version_id === currentVersionId ? " current" : ""}`}
                    key={v.version_id}
                  >
                    <div className="version-head">
                      <span className="version-number">v{v.version_number}</span>
                      {v.version_id === currentVersionId && (
                        <span className="version-current">当前</span>
                      )}
                    </div>
                    <div className="version-detail">
                      {v.instruction ?? "初始版本"} · {new Date(v.created_at).toLocaleString()}
                    </div>
                    {v.version_id !== currentVersionId && (
                      <button className="restore-btn" onClick={() => handleRestore(v.version_id)}>
                        恢复此版本
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </details>

          <details className="panel result">
            <summary>
              <h2>混音器</h2>
            </summary>
            <MixerPanel
              songId={songId}
              refreshKey={pianoRefreshKey}
              onApplied={handleMixApplied}
              onError={(msg) => setError(msg)}
            />
          </details>

          <details className="panel result">
            <summary>
              <h2>分轨导出</h2>
            </summary>
            <StemExportPanel songId={songId} onError={(msg) => setError(msg)} />
          </details>
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
