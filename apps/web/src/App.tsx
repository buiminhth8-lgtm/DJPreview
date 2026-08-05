import { useState } from "react";
import type {
  AudioMetadata,
  AssetsResponse,
  DiffItem,
  GenerateFromReferenceResponse,
  OptimizeResponse,
  RegenerationResult,
} from "./api/types";
import { useAudioAssets, useSongProject, useStyles, useVersions } from "./hooks";
import ArrangementInspector from "./components/ArrangementInspector";
import AudioPlayer from "./components/AudioPlayer";
import EvaluationPanel from "./components/EvaluationPanel";
import MixerPanel from "./components/MixerPanel";
import ProjectIOPanel from "./components/ProjectIOPanel";
import ReferenceMidiPanel from "./components/ReferenceMidiPanel";
import RegenerationPanel from "./components/RegenerationPanel";
import StemExportPanel from "./components/StemExportPanel";
import StyleTemplatePanel from "./components/StyleTemplatePanel";

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
  const project = useSongProject();
  const styles = useStyles();
  const [styleStrength, setStyleStrength] = useState(0.7);
  const [pianoRefreshKey, setPianoRefreshKey] = useState(0);
  const [lastDiff, setLastDiff] = useState<DiffItem[] | null>(null);

  const audio = useAudioAssets(project.songId);
  const versions = useVersions({ songId: project.songId });

  const loadProject = async (newSongId: string) => {
    const spec = await project.loadSong(newSongId);
    if (!spec) return;
    audio.resetAssets();
    versions.resetVersions();
    setLastDiff(null);
    setPianoRefreshKey((k) => k + 1);
  };

  const handleGenerateSpec = async () => {
    audio.resetAssets();
    versions.resetVersions();
    setLastDiff(null);
    await project.generate(project.prompt, styles.selectedStyleId, styleStrength);
  };

  const handleGenerateFromReference = (result: GenerateFromReferenceResponse) => {
    void loadProject(result.song_id);
  };

  const handleImported = (newSongId: string) => {
    void loadProject(newSongId);
  };

  const handleGenerateMidi = async () => {
    await audio.generateMidi();
  };

  const handleRenderAudio = async () => {
    await audio.renderAudio();
  };

  const handleApplyEdit = async () => {
    const result = await project.edit(project.editInstruction);
    if (!result) return;
    setLastDiff(result.diff);
    audio.updateFromAssets(result.assets);
    await versions.refreshVersions();
    setPianoRefreshKey((k) => k + 1);
  };

  const handleLoadVersions = async () => {
    await versions.refreshVersions();
  };

  const handleRestore = async (versionId: string) => {
    const result = await versions.restoreVersion(versionId);
    if (!result) return;
    project.setMusicSpec(result.music_spec);
    audio.updateFromAssets(result.assets);
    await versions.refreshVersions();
    setPianoRefreshKey((k) => k + 1);
  };

  const handleMixApplied = (assets: AssetsResponse) => {
    audio.updateFromAssets(assets);
    setPianoRefreshKey((k) => k + 1);
  };

  const handleOptimized = async (result: OptimizeResponse) => {
    project.setMusicSpec(result.music_spec);
    audio.updateFromAssets(result.assets);
    await versions.refreshVersions();
    setPianoRefreshKey((k) => k + 1);
  };

  const handleRegenerated = async (result: RegenerationResult) => {
    project.setMusicSpec(result.music_spec);
    audio.updateFromAssets(result.assets);
    await versions.refreshVersions();
    setPianoRefreshKey((k) => k + 1);
  };

  return (
    <div className="container">
      <header>
        <h1>AI Music MVP</h1>
        <p className="subtitle">
          生成 → MIDI → WAV → 修改/版本 → 混音/可视化/质量 → 风格/参考/重生成/评估
        </p>
      </header>

      <section className="panel">
        <textarea
          value={project.prompt}
          onChange={(e) => project.setPrompt(e.target.value)}
          placeholder="例如：生成一段忧郁空灵的钢琴配乐，72 BPM，D 小调"
          rows={4}
          disabled={project.loadingSpec}
        />
        <StyleTemplatePanel
          value={styles.selectedStyleId}
          strength={styleStrength}
          onChange={(id, strength) => {
            styles.setSelectedStyleId(id);
            setStyleStrength(strength);
          }}
          onError={(msg) => project.setError(msg)}
        />
        <div className="actions">
          <button onClick={handleGenerateSpec} disabled={project.loadingSpec}>
            {project.loadingSpec ? "生成中…" : "生成 MusicSpec"}
          </button>
        </div>
      </section>

      {project.error && <div className="error">⚠ {project.error}</div>}

      {project.musicSpec && project.songId && (
        <>
          <section className="panel result">
            <h2>播放与下载</h2>
            <p className="song-id">
              song_id：<code>{project.songId}</code>
            </p>
            <div className="midi-actions">
              <button onClick={handleGenerateMidi} disabled={audio.loadingMidi}>
                {audio.loadingMidi ? "MIDI 生成中…" : "生成 MIDI"}
              </button>
              {audio.midiDownloadUrl && (
                <a className="download-link" href={audio.midiDownloadUrl} download={`${project.songId}.mid`}>
                  下载 MIDI
                </a>
              )}
            </div>
            {audio.midiResult && (
              <div className="summary">
                <div className="summary-row">
                  <span className="summary-label">轨道数</span>
                  <span className="summary-value">{audio.midiResult.summary.tracks}</span>
                </div>
                <div className="summary-row">
                  <span className="summary-label">小节数</span>
                  <span className="summary-value">{audio.midiResult.summary.bars}</span>
                </div>
                <div className="summary-row">
                  <span className="summary-label">BPM</span>
                  <span className="summary-value">{audio.midiResult.summary.bpm}</span>
                </div>
              </div>
            )}
            <div className="midi-actions">
              <button onClick={handleRenderAudio} disabled={audio.loadingAudio}>
                {audio.loadingAudio ? "WAV 渲染中…" : "渲染 WAV"}
              </button>
            </div>
            {audio.audioResult && audio.audioStreamUrl && (
              <>
                <AudioPlayer audioUrl={audio.audioStreamUrl} downloadUrl={audio.audioDownloadUrl ?? ""} />
                <AudioMeta metadata={audio.audioResult.metadata} />
              </>
            )}
          </section>

          <details className="panel result" open>
            <summary>
              <h2>编曲检查（摘要 / 段落 / 轨道 / 钢琴卷帘 / 质量）</h2>
            </summary>
            <ArrangementInspector
              songId={project.songId}
              spec={project.musicSpec}
              refreshKey={pianoRefreshKey}
              onOptimized={(result) => void handleOptimized(result)}
              onError={(msg) => project.setError(msg)}
            />
          </details>

          <details className="panel result">
            <summary>
              <h2>自然语言修改与版本管理</h2>
            </summary>
            <textarea
              value={project.editInstruction}
              onChange={(e) => project.setEditInstruction(e.target.value)}
              placeholder="例如：副歌更亮一点 / 整首更快一点 / 加点中国风 / 去掉贝斯 / 副歌加鼓"
              rows={3}
              disabled={project.loadingEdit}
            />
            <div className="actions">
              <button onClick={handleApplyEdit} disabled={project.loadingEdit}>
                {project.loadingEdit ? "修改中…" : "应用修改"}
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
              <button onClick={handleLoadVersions} disabled={versions.loadingVersions}>
                {versions.loadingVersions ? "加载中…" : "查看版本"}
              </button>
            </div>
            {versions.versions && (
              <div className="version-list">
                {[...versions.versions].reverse().map((v) => (
                  <div
                    className={`version-item${v.version_id === versions.currentVersionId ? " current" : ""}`}
                    key={v.version_id}
                  >
                    <div className="version-head">
                      <span className="version-number">v{v.version_number}</span>
                      {v.version_id === versions.currentVersionId && (
                        <span className="version-current">当前</span>
                      )}
                    </div>
                    <div className="version-detail">
                      {v.instruction ?? "初始版本"} · {new Date(v.created_at).toLocaleString()}
                    </div>
                    {v.version_id !== versions.currentVersionId && (
                      <button className="restore-btn" onClick={() => void handleRestore(v.version_id)}>
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
              songId={project.songId}
              refreshKey={pianoRefreshKey}
              onApplied={handleMixApplied}
              onError={(msg) => project.setError(msg)}
            />
          </details>

          <details className="panel result">
            <summary>
              <h2>分轨导出</h2>
            </summary>
            <StemExportPanel songId={project.songId} onError={(msg) => project.setError(msg)} />
          </details>

          <details className="panel result">
            <summary>
              <h2>局部重生成</h2>
            </summary>
            <RegenerationPanel
              songId={project.songId}
              spec={project.musicSpec}
              onRegenerated={(result) => void handleRegenerated(result)}
              onError={(msg) => project.setError(msg)}
            />
          </details>

          <details className="panel result">
            <summary>
              <h2>参考 MIDI 分析与生成</h2>
            </summary>
            <ReferenceMidiPanel
              styleTemplateId={styles.selectedStyleId || null}
              styleStrength={styleStrength}
              onGenerated={handleGenerateFromReference}
              onError={(msg) => project.setError(msg)}
            />
          </details>

          <details className="panel result">
            <summary>
              <h2>工程导入导出</h2>
            </summary>
            <ProjectIOPanel
              songId={project.songId}
              onImported={handleImported}
              onError={(msg) => project.setError(msg)}
            />
          </details>

          <details className="panel result">
            <summary>
              <h2>批量评估</h2>
            </summary>
            <EvaluationPanel onError={(msg) => project.setError(msg)} />
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
