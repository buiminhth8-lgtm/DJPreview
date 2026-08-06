// GenerateConsole：生成控制台（T38-D）。
// 展示 prompt 输入、Provider/Model 状态、生成相关按钮（带 disabled 原因）。
// 不直接发 API 请求，只通过 props 接收状态与 handler。

import StyleTemplatePanel from "../StyleTemplatePanel";
import { ActionButton, ButtonRow, InlineNotice, SectionCard, StatusBadge } from "../ui";

export interface GenerateConsoleProps {
  prompt: string;
  onPromptChange: (value: string) => void;

  provider?: string | null;
  model?: string | null;
  reasoningEffort?: string | null;
  responseFormatEnabled?: boolean | null;

  isGeneratingSpec?: boolean;
  isGeneratingMidi?: boolean;
  isRenderingAudio?: boolean;

  hasMusicSpec?: boolean;
  hasMidi?: boolean;
  hasAudio?: boolean;
  hasSong?: boolean;

  onGenerateSpec: () => void;
  onGenerateMidi?: () => void;
  onRenderAudio?: () => void;
  onGenerateFullSong?: () => void;

  lastRequestId?: string | null;
  errorMessage?: string | null;

  // 可选：风格模板（保留现有样式选择能力）
  styleId?: string;
  styleStrength?: number;
  onStyleChange?: (styleId: string, strength: number) => void;
  onError?: (message: string) => void;
}

export function GenerateConsole({
  prompt,
  onPromptChange,
  provider,
  model,
  reasoningEffort,
  responseFormatEnabled,
  isGeneratingSpec = false,
  isGeneratingMidi = false,
  isRenderingAudio = false,
  hasMusicSpec = false,
  hasMidi = false,
  hasAudio = false,
  hasSong = false,
  onGenerateSpec,
  onGenerateMidi,
  onRenderAudio,
  onGenerateFullSong,
  lastRequestId,
  errorMessage,
  styleId,
  styleStrength = 0.7,
  onStyleChange,
  onError,
}: GenerateConsoleProps) {
  const promptEmpty = prompt.trim().length === 0;

  return (
    <SectionCard
      title="生成控制台"
      description="描述你想生成的音乐"
      badge={
        <StatusBadge variant="primary" title="当前 LLM Provider">
          Provider：{provider || "未知"}
        </StatusBadge>
      }
    >
      <div className="generate-console">
        <label className="generate-console__label" htmlFor="generate-prompt">
          音乐描述
        </label>
        <textarea
          id="generate-prompt"
          className="generate-console__textarea"
          value={prompt}
          onChange={(e) => onPromptChange(e.target.value)}
          placeholder="例如：游戏 Boss 战音乐，E minor，140 BPM，4/4，包含 string ostinato、brass、distortion guitar、heavy drums、synth bass；节奏紧张，副歌或 climax 更强烈。"
          rows={5}
          disabled={isGeneratingSpec}
        />

        {onStyleChange && (
          <StyleTemplatePanel
            value={styleId ?? ""}
            strength={styleStrength}
            onChange={onStyleChange}
            onError={onError ?? (() => undefined)}
          />
        )}

        <div className="generate-console__provider">
          <StatusBadge variant="neutral" title="模型">
            Model：{model || "未知"}
          </StatusBadge>
          {reasoningEffort && (
            <StatusBadge variant="neutral" title="reasoning_effort">
              reasoning_effort：{reasoningEffort}
            </StatusBadge>
          )}
          <StatusBadge variant={responseFormatEnabled === false ? "neutral" : "info"} title="response_format">
            response_format：{responseFormatEnabled === undefined || responseFormatEnabled === null ? "unknown" : responseFormatEnabled ? "enabled" : "disabled"}
          </StatusBadge>
        </div>

        <ButtonRow className="generate-console__actions">
          <ActionButton
            variant="primary"
            onClick={onGenerateSpec}
            disabled={promptEmpty || isGeneratingSpec}
            disabledReason={promptEmpty ? "请输入音乐描述" : undefined}
            loading={isGeneratingSpec}
          >
            {isGeneratingSpec ? "正在生成 MusicSpec…" : "生成 MusicSpec"}
          </ActionButton>

          {onGenerateMidi && (
            <ActionButton
              variant="secondary"
              onClick={onGenerateMidi}
              disabled={!hasSong || !hasMusicSpec || isGeneratingMidi}
              disabledReason={!hasMusicSpec ? "请先生成 MusicSpec" : undefined}
              loading={isGeneratingMidi}
            >
              {isGeneratingMidi ? "MIDI 生成中…" : "生成 MIDI"}
            </ActionButton>
          )}

          {onRenderAudio && (
            <ActionButton
              variant="secondary"
              onClick={onRenderAudio}
              disabled={!hasMidi || isRenderingAudio}
              disabledReason={!hasMidi ? "请先生成 MIDI" : undefined}
              loading={isRenderingAudio}
            >
              {isRenderingAudio ? "WAV 渲染中…" : "渲染 WAV"}
            </ActionButton>
          )}

          {onGenerateFullSong && (
            <ActionButton
              variant="ghost"
              onClick={onGenerateFullSong}
              disabled={promptEmpty || isGeneratingSpec}
              disabledReason={promptEmpty ? "请输入音乐描述" : undefined}
            >
              生成完整歌曲
            </ActionButton>
          )}
        </ButtonRow>

        <div className="generate-console__status">
          <StatusBadge variant={hasAudio ? "success" : hasMidi ? "info" : "neutral"}>
            {hasAudio ? "WAV ready" : hasMidi ? "MIDI ready" : hasMusicSpec ? "MusicSpec ready" : "尚未生成"}
          </StatusBadge>
          {hasSong && <StatusBadge variant="success">工程就绪</StatusBadge>}
          {lastRequestId && (
            <StatusBadge variant="neutral" title="最近请求">
              req: {lastRequestId.slice(0, 8)}…
            </StatusBadge>
          )}
        </div>

        {errorMessage && (
          <InlineNotice variant="danger" title="生成失败">
            {errorMessage}
          </InlineNotice>
        )}
      </div>
    </SectionCard>
  );
}
