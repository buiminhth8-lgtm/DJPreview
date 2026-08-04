import { useState } from "react";
import {
  API_BASE_URL,
  generateMidi,
  generateMusicSpec,
  type GenerateMidiResponse,
  type MusicSpec,
} from "./api/musicApi";

interface SummaryItem {
  label: string;
  value: string;
}

function buildSummary(spec: MusicSpec): SummaryItem[] {
  return [
    { label: "标题", value: spec.title },
    { label: "BPM", value: `${spec.tempo.bpm}${spec.tempo.feel ? `（${spec.tempo.feel}）` : ""}` },
    {
      label: "调性",
      value: `${spec.tonality.key} ${spec.tonality.mode}${spec.tonality.scale ? ` · ${spec.tonality.scale}` : ""}`,
    },
    { label: "小节数", value: `${spec.length.bars} bars` },
    { label: "拍号", value: `${spec.meter.numerator}/${spec.meter.denominator}` },
    { label: "风格", value: spec.style.join(", ") || "—" },
    { label: "情绪", value: spec.mood.join(", ") || "—" },
    {
      label: "段落",
      value: spec.form.map((s) => `${s.id}(${s.start_bar}-${s.start_bar + s.bars - 1})`).join(" / "),
    },
    {
      label: "轨道",
      value: spec.tracks.map((t) => `${t.id}(${t.instrument})`).join(" / "),
    },
  ];
}

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [songId, setSongId] = useState<string | null>(null);
  const [spec, setSpec] = useState<MusicSpec | null>(null);
  const [midiLoading, setMidiLoading] = useState(false);
  const [midiResult, setMidiResult] = useState<GenerateMidiResponse | null>(null);

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setError("请输入音乐描述");
      return;
    }
    setLoading(true);
    setError(null);
    setMidiResult(null);
    try {
      const result = await generateMusicSpec(prompt.trim());
      setSongId(result.song_id);
      setSpec(result.music_spec);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateMidi = async () => {
    if (!songId) {
      return;
    }
    setMidiLoading(true);
    setError(null);
    try {
      const result = await generateMidi(songId);
      setMidiResult(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setMidiLoading(false);
    }
  };

  return (
    <div className="container">
      <header>
        <h1>AI Music MVP</h1>
        <p className="subtitle">输入一句话，生成 MusicSpec v0.1 音乐方案并导出标准 MIDI</p>
      </header>

      <section className="panel">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="例如：生成一段忧郁空灵的钢琴配乐，72 BPM，D 小调"
          rows={4}
          disabled={loading}
        />
        <div className="actions">
          <button onClick={handleGenerate} disabled={loading}>
            {loading ? "生成中…" : "生成 MusicSpec"}
          </button>
        </div>
      </section>

      {error && <div className="error">⚠ {error}</div>}

      {spec && (
        <section className="panel result">
          <h2>生成结果</h2>
          <p className="song-id">
            song_id：<code>{songId}</code>
          </p>

          <div className="summary">
            {buildSummary(spec).map((item) => (
              <div className="summary-row" key={item.label}>
                <span className="summary-label">{item.label}</span>
                <span className="summary-value">{item.value}</span>
              </div>
            ))}
          </div>

          <div className="midi-actions">
            <button onClick={handleGenerateMidi} disabled={midiLoading}>
              {midiLoading ? "MIDI 生成中…" : "生成 MIDI"}
            </button>
            {midiResult && (
              <div className="midi-result">
                <p>
                  MIDI 已生成：
                  <a
                    className="download-link"
                    href={`${API_BASE_URL}${midiResult.download_url}`}
                    download={`${midiResult.song_id}.mid`}
                  >
                    下载 {midiResult.midi_file}
                  </a>
                </p>
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
              </div>
            )}
          </div>

          <h3>MusicSpec JSON</h3>
          <pre>{JSON.stringify(spec, null, 2)}</pre>
        </section>
      )}
    </div>
  );
}
