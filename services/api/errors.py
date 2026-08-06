"""统一 API 错误响应辅助模块。

错误响应结构（T35）：
{
  "success": false,
  "request_id": "<request_id>",
  "error": {
    "code": "<error_code>",
    "message": "...",
    "stage": "<stage>",
    "provider": "<provider>",
    "status_code": 502,
    "details": {...}
  }
}
兼容旧字段 error_code / message / details（保留在顶层）。
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


class ApiErrorCode:
    """稳定的机器可读错误码。"""

    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    VERSION_NOT_FOUND = "VERSION_NOT_FOUND"
    ASSET_NOT_FOUND = "ASSET_NOT_FOUND"
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_PROJECT_BUNDLE = "INVALID_PROJECT_BUNDLE"
    MUSIC_SPEC_VALIDATION_FAILED = "MUSIC_SPEC_VALIDATION_FAILED"
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    LLM_PROVIDER_ERROR = "LLM_PROVIDER_ERROR"
    UNKNOWN_PROVIDER = "UNKNOWN_PROVIDER"
    LLM_HTTP_ERROR = "LLM_HTTP_ERROR"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_INVALID_RESPONSE = "LLM_INVALID_RESPONSE"
    JSON_PARSE_ERROR = "JSON_PARSE_ERROR"
    MUSIC_SPEC_PARSE_ERROR = "MUSIC_SPEC_PARSE_ERROR"
    MUSIC_SPEC_VALIDATION_ERROR = "MUSIC_SPEC_VALIDATION_ERROR"
    RENDER_FAILED = "RENDER_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorStage:
    """错误发生的阶段，用于前端定位。"""

    REQUEST_VALIDATION = "request_validation"
    PROVIDER_SELECTION = "provider_selection"
    LLM_CALL = "llm_call"
    LLM_RESPONSE_PARSE = "llm_response_parse"
    JSON_REPAIR = "json_repair"
    MUSIC_SPEC_PARSE = "music_spec_parse"
    MUSIC_SPEC_VALIDATION = "music_spec_validation"
    MUSIC_SPEC_NORMALIZE = "music_spec_normalize"
    PROJECT_CREATE = "project_create"
    UNKNOWN = "unknown"


def api_error(
    status_code: int,
    error_code: str,
    message: str,
    details: dict[str, Any] | None = None,
    *,
    stage: str = ErrorStage.UNKNOWN,
    provider: str | None = None,
    status: int | None = None,
) -> HTTPException:
    """构造统一错误响应（detail 为结构化 dict，由全局 handler 展开）。"""
    return HTTPException(
        status_code=status_code,
        detail={
            "error_code": error_code,
            "message": message,
            "details": details or {},
            "stage": stage,
            "provider": provider,
            "status": status if status is not None else status_code,
        },
    )


def project_not_found(song_id: str | None = None) -> HTTPException:
    return api_error(
        404,
        ApiErrorCode.PROJECT_NOT_FOUND,
        "项目不存在",
        {"song_id": song_id} if song_id else {},
    )


def version_not_found(song_id: str | None = None, version_id: str | None = None) -> HTTPException:
    return api_error(
        404,
        ApiErrorCode.VERSION_NOT_FOUND,
        "版本不存在",
        {"song_id": song_id, "version_id": version_id},
    )


def task_not_found(task_id: str | None = None) -> HTTPException:
    return api_error(
        404,
        ApiErrorCode.TASK_NOT_FOUND,
        "任务不存在",
        {"task_id": task_id} if task_id else {},
    )


def asset_not_found(asset: str | None = None, message: str = "资源不存在") -> HTTPException:
    return api_error(404, ApiErrorCode.ASSET_NOT_FOUND, message, {"asset": asset} if asset else {})


def invalid_request(
    message: str = "请求无效",
    details: dict[str, Any] | None = None,
    *,
    stage: str = ErrorStage.REQUEST_VALIDATION,
) -> HTTPException:
    return api_error(400, ApiErrorCode.INVALID_REQUEST, message, details, stage=stage)


def invalid_bundle(reason: str = "工程文件无效") -> HTTPException:
    return api_error(400, ApiErrorCode.INVALID_PROJECT_BUNDLE, "工程文件无效", {"reason": reason})


def spec_validation_failed(
    message: str = "MusicSpec 校验失败",
    details: dict[str, Any] | None = None,
    *,
    status_code: int = 400,
    stage: str = ErrorStage.MUSIC_SPEC_VALIDATION,
) -> HTTPException:
    return api_error(
        status_code,
        ApiErrorCode.MUSIC_SPEC_VALIDATION_FAILED,
        message,
        details,
        stage=stage,
        status=status_code,
    )


def llm_error(
    message: str = "模型调用失败",
    details: dict[str, Any] | None = None,
    *,
    stage: str = ErrorStage.LLM_CALL,
    provider: str | None = None,
) -> HTTPException:
    """通用 LLM 错误（502）。"""
    return api_error(502, ApiErrorCode.LLM_PROVIDER_ERROR, message, details, stage=stage, provider=provider)


def llm_http_error(
    message: str,
    details: dict[str, Any] | None = None,
    *,
    status_code: int = 502,
    provider: str | None = None,
) -> HTTPException:
    """LLM 上游 HTTP 错误（如 401 / 500），HTTP 状态码透传上游。"""
    return api_error(
        status_code,
        ApiErrorCode.LLM_HTTP_ERROR,
        message,
        details,
        stage=ErrorStage.LLM_CALL,
        provider=provider,
        status=status_code,
    )


def llm_timeout(
    message: str = "LLM 请求超时",
    details: dict[str, Any] | None = None,
    *,
    provider: str | None = None,
) -> HTTPException:
    return api_error(
        504,
        ApiErrorCode.LLM_TIMEOUT,
        message,
        details,
        stage=ErrorStage.LLM_CALL,
        provider=provider,
    )


def llm_invalid_response(
    message: str = "LLM 输出解析失败",
    details: dict[str, Any] | None = None,
    *,
    provider: str | None = None,
) -> HTTPException:
    return api_error(
        502,
        ApiErrorCode.LLM_INVALID_RESPONSE,
        message,
        details,
        stage=ErrorStage.LLM_RESPONSE_PARSE,
        provider=provider,
    )


def json_parse_error(
    message: str = "JSON 解析失败",
    details: dict[str, Any] | None = None,
    *,
    provider: str | None = None,
) -> HTTPException:
    return api_error(
        502,
        ApiErrorCode.JSON_PARSE_ERROR,
        message,
        details,
        stage=ErrorStage.LLM_RESPONSE_PARSE,
        provider=provider,
    )


def unknown_provider(
    provider_name: str | None = None,
    details: dict[str, Any] | None = None,
) -> HTTPException:
    return api_error(
        500,
        ApiErrorCode.UNKNOWN_PROVIDER,
        f"未知的 LLM Provider：{provider_name or ''}",
        details,
        stage=ErrorStage.PROVIDER_SELECTION,
    )


def render_failed(message: str = "音频渲染失败") -> HTTPException:
    return api_error(500, ApiErrorCode.RENDER_FAILED, message)


def internal_error(message: str = "服务器内部错误", details: dict[str, Any] | None = None) -> HTTPException:
    return api_error(500, ApiErrorCode.INTERNAL_ERROR, message, details, stage=ErrorStage.UNKNOWN)
