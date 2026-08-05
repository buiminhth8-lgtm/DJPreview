// 风格模板领域 API。

import { requestJson } from "./client";
import type { StyleTemplateSpec } from "./types";

export function listStyles(): Promise<StyleTemplateSpec[]> {
  return requestJson("/api/v1/styles", "GET");
}

export function getStyle(id: string): Promise<StyleTemplateSpec> {
  return requestJson(`/api/v1/styles/${id}`, "GET");
}
