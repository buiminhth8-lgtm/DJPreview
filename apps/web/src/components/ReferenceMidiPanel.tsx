import { useRef, useState } from "react";
import {
  analyzeReferenceMidi,
  generateFromReference,
  type GenerateFromReferenceResponse,
  type ReferenceMidiAnalysis,
} from "../api/musicApi";

interface ReferenceMidiPanelProps {
  styleTemplateId?: string | null;
  styleStrength?: number;
  onGenerated: (result: GenerateFromReferenceResponse) => void;
  onError: (message: string) => void;
}

export default function ReferenceMidiPanel({
  styleTemplateId,
  styleStrength = 0.7,
  onGenerated,
  onError,
}: ReferenceMidiPanelProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<ReferenceMidiAnalysis | null>(null);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);

  const handleAnalyze = async () => {
    if (!file) {
      onError("请先选择 .mid / .midi 文件");
      return;
    }
    setBusy(true);
    try {
      const result = await analyzeReferenceMidi(file);
      setAnalysis(result);
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const handleGenerate = async () => {
    if (!file || !prompt.trim()) {
      onError("请选择参考 MIDI 并输入描述");
      return;
    }
    setBusy(true);
    try {
      const result = await generateFromReference(file, prompt.trim(), styleTemplateId, styleStrength);
      onGenerated(result);
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="reference-panel">
      <input
        type="file"
        accept=".mid,.midi"
        ref={fileRef}
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />
      <div className="actions">
        <button onClick={handleAnalyze} disabled={busy || !file}>
          {busy ? "分析中…" : "分析参考 MIDI"}
        </button>
      </div>
      <p className="muted-note">
        提示：系统只提取速度、密度、音域、节奏、能量等高层特征，不复制参考旋律。
      </p>
      {analysis && (
        <div className="summary reference-summary">
          <div className="summary-row">
            <span className="summary-label">BPM</span>
            <span className="summary-value">{analysis.bpm ?? "未知"}</span>
          </div>
          <div className="summary-row">
            <span className="summary-label">轨道数</span>
            <span className="summary-value">{analysis.track_count}</span>
          </div>
          <div className="summary-row">
            <span className="summary-label">音符数</span>
            <span className="summary-value">{analysis.note_count}</span>
          </div>
          <div className="summary-row">
            <span className="summary-label">音域</span>
            <span className="summary-value">
              {analysis.pitch_range.min ?? "?"} - {analysis.pitch_range.max ?? "?"}
            </span>
          </div>
          <div className="summary-row">
            <span className="summary-label">密度</span>
            <span className="summary-value">{analysis.density.notes_per_bar} notes/bar</span>
          </div>
          <div className="summary-row">
            <span className="summary-label">风格标签</span>
            <span className="summary-value">{analysis.suggested_style_tags.join(" / ") || "—"}</span>
          </div>
        </div>
      )}
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="例如：生成一段类似能量变化但旋律不同的配乐"
        rows={2}
      />
      <div className="actions">
        <button onClick={handleGenerate} disabled={busy || !file || !prompt.trim()}>
          {busy ? "生成中…" : "基于参考生成"}
        </button>
      </div>
    </div>
  );
}
