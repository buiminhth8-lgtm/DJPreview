// 统一 fetch client：API base URL、结构化错误解析（T35）、request_id、下载辅助。

// 后端 API 地址可通过 VITE_API_BASE_URL 配置；默认空字符串表示相对路径 /api/v1
// （开发环境由 Vite proxy 转发；生产环境可配置 VITE_API_BASE_URL 指向后端）
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export const MAX_PREVIEW_CHARS = 2000;

export interface ApiErrorDetail {
  code?: string;
  message?: string;
  stage?: string;
  provider?: string;
  status_code?: number;
  details?: Record<string, unknown>;
}

export interface ApiErrorResponse {
  success?: boolean;
  request_id?: string;
  error_code?: string;
  message?: string;
  details?: Record<string, unknown>;
  error?: ApiErrorDetail;
  detail?: unknown;
}

export class ApiRequestError extends Error {
  status: number;
  code?: string;
  stage?: string;
  provider?: string;
  requestId?: string;
  details?: Record<string, unknown>;
  rawBodyPreview?: string;

  constructor(
    message: string,
    options: {
      status: number;
      code?: string;
      stage?: string;
      provider?: string;
      requestId?: string;
      details?: Record<string, unknown>;
      rawBodyPreview?: string;
    },
  ) {
    super(message);
    this.name = "ApiRequestError";
    this.status = options.status;
    this.code = options.code;
    this.stage = options.stage;
    this.provider = options.provider;
    this.requestId = options.requestId;
    this.details = options.details;
    this.rawBodyPreview = options.rawBodyPreview;
  }
}

function _truncate(text: string, max = MAX_PREVIEW_CHARS): string {
  return text.length > max ? `${text.slice(0, max)}…（已截断）` : text;
}

export async function parseApiError(
  response: Response,
  rawBodyPreview?: string,
): Promise<ApiRequestError> {
  const requestId = response.headers.get("X-Request-ID") ?? undefined;
  let body: ApiErrorResponse | null = null;
  let preview = rawBodyPreview;
  try {
    body = (await response.json()) as ApiErrorResponse;
  } catch {
    body = null;
  }
  if (!preview && body) {
    preview = _truncate(JSON.stringify(body));
  }

  const error = body?.error;
  const code = error?.code ?? body?.error_code;
  const message = error?.message ?? body?.message;
  const stage = error?.stage;
  const provider = error?.provider;
  const details = error?.details ?? body?.details;
  const bodyRequestId = body?.request_id;

  // 兼容旧结构：detail 字符串 / detail 对象
  let fallbackMessage: string | undefined;
  if (!message) {
    if (typeof body?.detail === "string") fallbackMessage = body.detail;
    else if (body?.detail && typeof body.detail === "object") {
      const d = body.detail as ApiErrorResponse;
      fallbackMessage = d.message || `请求失败（HTTP ${response.status}）`;
    }
  }

  return new ApiRequestError(
    message || fallbackMessage || `请求失败（HTTP ${response.status}）`,
    {
      status: response.status,
      code,
      stage,
      provider,
      requestId: requestId ?? bodyRequestId,
      details,
      rawBodyPreview: preview,
    },
  );
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        ...(options?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...(options?.headers || {}),
      },
    });
  } catch (e) {
    // 网络错误：不是 HTTP 错误，也不是 JSON 解析错误
    throw new ApiRequestError(`网络请求失败：${(e as Error).message}`, {
      status: 0,
      code: "NETWORK_ERROR",
      stage: "network",
    });
  }
  if (!response.ok) {
    throw await parseApiError(response);
  }
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiRequestError(`响应不是合法 JSON（HTTP ${response.status}）`, {
      status: response.status,
      code: "INVALID_JSON_RESPONSE",
      requestId: response.headers.get("X-Request-ID") ?? undefined,
    });
  }
}

export async function apiDownloadBlob(path: string): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`);
  } catch (e) {
    throw new ApiRequestError(`网络请求失败：${(e as Error).message}`, {
      status: 0,
      code: "NETWORK_ERROR",
      stage: "network",
    });
  }
  if (!response.ok) {
    throw await parseApiError(response);
  }
  return response.blob();
}

async function requestJson<T>(url: string, method: string, payload?: unknown): Promise<T> {
  return apiFetch<T>(url, {
    method,
    body: payload !== undefined ? JSON.stringify(payload) : undefined,
    headers: payload !== undefined ? { "Content-Type": "application/json" } : undefined,
  });
}

async function requestForm<T>(url: string, form: FormData): Promise<T> {
  return apiFetch<T>(url, { method: "POST", body: form });
}

export function resolveUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

export { requestJson, requestForm };
