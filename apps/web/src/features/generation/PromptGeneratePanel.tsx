// features/generation/PromptGeneratePanel.tsx（T33.4）
// 一句话生成核心 UI：prompt + 风格模板 + 生成按钮。纯 UI，无 API 调用。

import { StyleTemplateSelector } from "./StyleTemplateSelector";
import type { StyleTemplateSpec } from "../../api/types";
import { ActionButton, InlineNotice } from "../../components/ui";

export interface PromptGeneratePanelProps {
  prompt: string;
  onPromptChange: (value: string) => void;
  styles: StyleTemplateSpec[];
  selectedStyleId: string;
  styleStrength: number;
  stylesLoadError?: string | null;
  isGenerating: boolean;
  error: string | null;
  onSelectStyle: (id: string) => void;
  onStyleStrengthChange: (value: number) => void;
  onGenerate: () => void;
}

export function PromptGeneratePanel({
  prompt,
  onPromptChange,
  styles,
  selectedStyleId,
  styleStrength,
  stylesLoadError,
  isGenerating,
  error,
  onSelectStyle,
  onStyleStrengthChange,
  onGenerate,
}: PromptGeneratePanelProps) {
  const promptEmpty = prompt.trim().length === 0;

  return (
    <div className="generate-panel">
      <label className="generate-panel__label" htmlFor="create-prompt">
        一句话描述你想要的音乐
      </label>
      <textarea
        id="create-prompt"
        className="generate-panel__textarea"
        value={prompt}
        onChange={(e) => onPromptChange(e.target.value)}
        placeholder="例如：生成一首雨夜电影感钢琴曲，情绪忧郁但有希望。"
        rows={5}
        disabled={isGenerating}
      />

      <StyleTemplateSelector
        styles={styles}
        selectedId={selectedStyleId}
        strength={styleStrength}
        loadError={stylesLoadError}
        onSelect={onSelectStyle}
        onStrengthChange={onStyleStrengthChange}
      />

      <ActionButton
        variant="primary"
        onClick={onGenerate}
        disabled={promptEmpty || isGenerating}
        disabledReason={promptEmpty ? "请输入音乐描述" : undefined}
        loading={isGenerating}
      >
        {isGenerating ? "生成中…" : "生成音乐"}
      </ActionButton>

      {error && (
        <InlineNotice variant="danger" title="生成失败">
          {error}
        </InlineNotice>
      )}
    </div>
  );
}
