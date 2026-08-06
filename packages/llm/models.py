"""LLM 调用相关数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LLMChatResult:
    """一次 Chat Completions 调用结果（含诊断元数据）。

    raw_response / finish_reason / usage 用于调试日志与 raw response 保存。
    """

    content: str = ""
    http_status: int | None = None
    finish_reason: str = "unknown"
    usage: dict[str, Any] | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)
    raw_response_path: str | None = None
    message_content_path: str | None = None
    response_format_enabled: bool | None = None
    response_format_type: str | None = None
    response_format_fallback_used: bool = False
    reasoning_effort: str | None = None


class LLMCallRecord(BaseModel):
    """一次 LLM 调用的审计日志记录（保证不包含 API Key / Authorization）。

    T35 增强：记录 request_id / http_status / content_chars / json_parse 等调试字段。
    raw_response_preview 仅在 LLM_DEBUG_LOG_CONTENT=true 时写入（最长 2000 字符）。
    """

    created_at: str = Field(default_factory=_utc_now_iso)
    project_id: str | None = None
    request_id: str | None = None
    task_name: str
    provider: str
    model: str
    request: dict[str, Any] = Field(default_factory=dict)
    response: dict[str, Any] | None = None
    parsed: dict[str, Any] | None = None
    error: str | None = None
    latency_ms: int | None = None
    http_status: int | None = None
    content_chars: int | None = None
    json_parse: str | None = None
    validation_warning_count: int | None = None
    raw_response_preview: str | None = None
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    raw_response_path: str | None = None
    message_content_path: str | None = None
