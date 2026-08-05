// 参考 MIDI 领域 API：分析、基于参考生成。

import { requestForm } from "./client";
import type { GenerateFromReferenceResponse, ReferenceMidiAnalysis } from "./types";

export function analyzeReferenceMidi(file: File): Promise<ReferenceMidiAnalysis> {
  const form = new FormData();
  form.append("file", file);
  return requestForm("/api/v1/reference/analyze", form);
}

export function generateFromReference(
  file: File,
  prompt: string,
  styleTemplateId?: string | null,
  styleStrength = 0.7,
): Promise<GenerateFromReferenceResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("prompt", prompt);
  if (styleTemplateId) {
    form.append("style_template_id", styleTemplateId);
    form.append("style_strength", String(styleStrength));
  }
  return requestForm("/api/v1/songs/generate-from-reference", form);
}
