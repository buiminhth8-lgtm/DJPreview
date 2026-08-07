// features/generation：创作流程（T33.4）。
// CreatePage → useGenerateSong → generationApi → backend。

export * from "./generationTypes";
export { generateSong } from "./generationApi";
export { useGenerateSong } from "./useGenerateSong";
export type { UseGenerateSongResult } from "./useGenerateSong";
export { PromptGeneratePanel } from "./PromptGeneratePanel";
export type { PromptGeneratePanelProps } from "./PromptGeneratePanel";
export { StyleTemplateSelector } from "./StyleTemplateSelector";
export type { StyleTemplateSelectorProps } from "./StyleTemplateSelector";
export { GeneratedProjectSummary } from "./GeneratedProjectSummary";
export type { GeneratedProjectSummaryProps } from "./GeneratedProjectSummary";
