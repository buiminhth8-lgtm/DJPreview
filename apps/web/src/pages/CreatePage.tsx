// CreatePage：/create 创作页（T33.4 独立版）。
// 只负责“创建新工程”：prompt + 风格模板 + 生成 + 摘要 + 进入工作台。
// 不承载 MIDI/version/tasks/SoundFont 深度状态；生成成功不自动跳转，
// 用户确认摘要后点击“进入工程工作台”。

import { useEffect } from "react";
import { useGenerateSong } from "../features/generation/useGenerateSong";
import { PromptGeneratePanel } from "../features/generation/PromptGeneratePanel";
import { GeneratedProjectSummary } from "../features/generation/GeneratedProjectSummary";
import { useStyles } from "../hooks";
import { SectionCard } from "../components/ui";

export default function CreatePage() {
  const gen = useGenerateSong();
  const styles = useStyles();

  useEffect(() => {
    void styles.loadStyles();
  }, [styles.loadStyles]);

  return (
    <div className="page page--create">
      <header className="create-page__header">
        <h1>创作新音乐</h1>
        <p>输入一句话描述，选择风格模板，生成属于你的音乐工程。</p>
      </header>

      <SectionCard title="生成音乐" description="描述你想生成的音乐">
        <PromptGeneratePanel
          prompt={gen.prompt}
          onPromptChange={gen.setPrompt}
          styles={styles.styles}
          selectedStyleId={gen.styleTemplateId}
          styleStrength={gen.styleStrength}
          stylesLoadError={styles.error}
          isGenerating={gen.isGenerating}
          error={gen.error}
          onSelectStyle={gen.setStyleTemplateId}
          onStyleStrengthChange={gen.setStyleStrength}
          onGenerate={() => void gen.generate()}
        />
      </SectionCard>

      {gen.result && <GeneratedProjectSummary summary={gen.result} />}
    </div>
  );
}
