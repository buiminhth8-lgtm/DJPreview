// LegacyCreateContent：T33.1 过渡组件（/create 页面内容）。
// 复用现有 GenerateConsole / 概览面板，生成成功后跳转 /projects/:songId。
// 后续 T33.4 再拆分为正式 generation feature。

import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAudioAssets, useSongProject, useStyles, useVersions } from "../../hooks";
import { WorkspaceSectionPlaceholder } from "../workspace";
import GenerationDebugPanel from "../workspace/GenerationDebugPanel";
import { GenerateConsole } from "../workspace/GenerateConsole";
import { MusicSpecPanel } from "../workspace/MusicSpecPanel";
import { ProjectOverviewPanel } from "../workspace/ProjectOverviewPanel";
import { WarningsPanel } from "../workspace/WarningsPanel";

export default function LegacyCreateContent() {
  const navigate = useNavigate();
  const songProject = useSongProject();
  const styles = useStyles();
  const [styleStrength, setStyleStrength] = useState(0.7);

  const audioAssets = useAudioAssets(songProject.songId);
  const versions = useVersions({ songId: songProject.songId });

  const spec = songProject.musicSpec;
  const songId = songProject.songId;

  const handleGenerate = async () => {
    const result = await songProject.generate(songProject.prompt, styles.selectedStyleId, styleStrength);
    if (result?.song_id) {
      navigate(`/projects/${result.song_id}`);
    }
  };

  const handleGenerateMidi = async () => {
    await audioAssets.generateMidi();
  };

  const handleRenderAudio = async () => {
    await audioAssets.renderAudio();
  };

  return (
    <div className="create-page">
      <div className="create-page__hero">
        <GenerateConsole
          prompt={songProject.prompt}
          onPromptChange={songProject.setPrompt}
          provider={songProject.generationDebug?.provider ?? songProject.generationErrorInfo?.provider}
          model={songProject.generationDebug?.model}
          reasoningEffort={null}
          responseFormatEnabled={null}
          isGeneratingSpec={songProject.loadingSpec}
          isGeneratingMidi={audioAssets.loadingMidi}
          isRenderingAudio={audioAssets.loadingAudio}
          hasMusicSpec={Boolean(spec)}
          hasMidi={Boolean(audioAssets.assets?.has_midi)}
          hasAudio={Boolean(audioAssets.assets?.has_audio)}
          hasSong={Boolean(songId)}
          onGenerateSpec={() => void handleGenerate()}
          onGenerateMidi={() => void handleGenerateMidi()}
          onRenderAudio={() => void handleRenderAudio()}
          lastRequestId={songProject.generationRequestId}
          errorMessage={songProject.error}
          styleId={styles.selectedStyleId}
          styleStrength={styleStrength}
          onStyleChange={(id, strength) => {
            styles.setSelectedStyleId(id);
            setStyleStrength(strength);
          }}
          onError={songProject.setError}
        />
      </div>

      <div className="create-page__result">
        {spec ? (
          <>
            <ProjectOverviewPanel
              songId={songId}
              currentVersionId={versions.currentVersionId}
              musicSpec={spec}
              warningCount={songProject.validation?.warnings.length ?? 0}
              hasMidi={Boolean(audioAssets.assets?.has_midi)}
              hasAudio={Boolean(audioAssets.assets?.has_audio)}
              lastRequestId={songProject.generationRequestId}
              audioRenderMetadata={audioAssets.audioRenderMetadata}
            />
            <MusicSpecPanel musicSpec={spec} requestId={songProject.generationRequestId} />
            <WarningsPanel warnings={songProject.generationWarnings} hasMusicSpec={Boolean(spec)} />
          </>
        ) : (
          <WorkspaceSectionPlaceholder
            title="生成音乐"
            emptyTitle="尚未生成工程"
            emptyDescription="输入音乐描述并点击「生成 MusicSpec」，成功后这里会显示新工程概览，并可进入工程工作台。"
          />
        )}
      </div>

      <GenerationDebugPanel
        status={songProject.generationStatus}
        log={songProject.generationLog}
        requestId={songProject.generationRequestId}
        debug={songProject.generationDebug}
        warnings={songProject.generationWarnings}
        errorInfo={songProject.generationErrorInfo}
        audioRenderMetadata={audioAssets.audioRenderMetadata}
      />
    </div>
  );
}
