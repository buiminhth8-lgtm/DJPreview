// 统一 fetch client：API base URL、错误解析（兼容 T08 统一错误结构）、下载辅助。

// 后端 API 地址可通过 VITE_API_BASE_URL 配置；默认空字符串表示相对路径 /api/v1
// （开发环境由 Vite proxy 转发，Docker 部署由 nginx 转发到 api:8000）
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export interface ApiErrorResponse {
  error_code?: string;
  message?: string;
  details?: Record<string, unknown>;
  detail?: unknown;
}

export class ApiRequestError extends Error {
  status: number;
  errorCode?: string;
  details?: Record<string, unknown>;

  constructor(
    message: string,
    options: {
      status: number;
      errorCode?: string;
      details?: Record<string, unknown>;
    },
  ) {
    super(message);
    this.name = "ApiRequestError";
    this.status = options.status;
    this.errorCode = options.errorCode;
    this.details = options.details;
  }
}

export async function parseApiError(response: Response): Promise<ApiRequestError> {
  try {
    const body = (await response.json()) as ApiErrorResponse;
    if (body?.message) {
      return new ApiRequestError(body.message, {
        status: response.status,
        errorCode: body.error_code,
        details: body.details,
      });
    }
    if (typeof body?.detail === "string") {
      return new ApiRequestError(body.detail, { status: response.status });
    }
    if (body?.detail && typeof body.detail === "object" && "message" in body.detail) {
      const detail = body.detail as ApiErrorResponse;
      return new ApiRequestError(detail.message || `请求失败（HTTP ${response.status}）`, {
        status: response.status,
        errorCode: detail.error_code,
        details: detail.details,
      });
    }
    return new ApiRequestError(`请求失败（HTTP ${response.status}）`, { status: response.status });
  } catch {
    return new ApiRequestError(`请求失败（HTTP ${response.status}）`, { status: response.status });
  }
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(options?.headers || {}),
    },
  });
  if (!response.ok) {
    throw await parseApiError(response);
  }
  return (await response.json()) as T;
}

export async function apiDownloadBlob(path: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}${path}`);
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
