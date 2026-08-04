"""统一 API 错误响应辅助模块。"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


class ApiErrorCode:
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    VERSION_NOT_FOUND = "VERSION_NOT_FOUND"
    ASSET_NOT_FOUND = "ASSET_NOT_FOUND"
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_PROJECT_BUNDLE = "INVALID_PROJECT_BUNDLE"
    MUSIC_SPEC_VALIDATION_FAILED = "MUSIC_SPEC_VALIDATION_FAILED"
    LLM_PROVIDER_ERROR = "LLM_PROVIDER_ERROR"
    RENDER_FAILED = "RENDER_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


def api_error(
    status_code: int,
    error_code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> HTTPException:
    """构造统一错误响应（detail 为结构化 dict，由全局 handler 展开）。"""
    return HTTPException(
        status_code=status_code,
        detail={
            "error_code": error_code,
            "message": message,
            "details": details or {},
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


def asset_not_found(asset: str | None = None, message: str = "资源不存在") -> HTTPException:
    return api_error(404, ApiErrorCode.ASSET_NOT_FOUND, message, {"asset": asset} if asset else {})


def invalid_request(message: str = "请求无效", details: dict[str, Any] | None = None) -> HTTPException:
    return api_error(400, ApiErrorCode.INVALID_REQUEST, message, details)


def invalid_bundle(reason: str = "工程文件无效") -> HTTPException:
    return api_error(400, ApiErrorCode.INVALID_PROJECT_BUNDLE, "工程文件无效", {"reason": reason})


def spec_validation_failed(message: str = "MusicSpec 校验失败") -> HTTPException:
    return api_error(400, ApiErrorCode.MUSIC_SPEC_VALIDATION_FAILED, message)


def llm_error(message: str = "模型调用失败", details: dict[str, Any] | None = None) -> HTTPException:
    return api_error(502, ApiErrorCode.LLM_PROVIDER_ERROR, message, details)


def render_failed(message: str = "音频渲染失败") -> HTTPException:
    return api_error(500, ApiErrorCode.RENDER_FAILED, message)


def internal_error(message: str = "服务器内部错误") -> HTTPException:
    return api_error(500, ApiErrorCode.INTERNAL_ERROR, message)
