// 生成面板：prompt + 风格 + 生成按钮 + validation 提示。

import type { ValidationResult } from "../../api/types";
import StyleTemplatePanel from "../StyleTemplatePanel";

export interface GeneratePanelProps {
  prompt: string;
  loading: boolean;
  styleId: string;
  styleStrength: number;
  validation: ValidationResult | null | undefined;
  onPromptChange: (value: string) => void;
  onStyleChange: (id: string, strength: number) => void;
  onError: (message: string) => void;
  onGenerate: () => void;
}

export default function GeneratePanel({
  prompt,
  loading,
  styleId,
  styleStrength,
  validation,
  onPromptChange,
  onStyleChange,
  onError,
  onGenerate,
}: GeneratePanelProps) {
  return (
    <section className="panel">
      <h2>生成 MusicSpec</h2>
      <textarea
        value={prompt}
        onChange={(e) => onPromptChange(e.target.value)}
        placeholder="例如：生成一段忧郁空灵的钢琴配乐，72 BPM，D 小调"
        rows={4}
        disabled={loading}
      />
      <StyleTemplatePanel value={styleId} strength={styleStrength} onChange={onStyleChange} onError={onError} />
      <div className="actions">
        <button onClick={onGenerate} disabled={loading}>
          {loading ? "生成中…" : "生成 MusicSpec"}
        </button>
      </div>
      {validation && (validation.warnings.length > 0 || validation.errors.length > 0) && (
        <div className="validation-box">
          {validation.warnings.map((w) => (
            <div className="warning" key={`${w.code}-${w.message}`}>
              ⚠ {w.message}
            </div>
          ))}
          {validation.errors.map((e) => (
            <div className="error" key={`${e.code}-${e.message}`}>
              ✗ {e.message}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
