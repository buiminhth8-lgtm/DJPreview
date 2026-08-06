"""LLM 调试日志配置与 raw response 保存。

环境变量：
  LLM_DEBUG_LOG_CONTENT          console 打印 message content preview（默认 false）
  LLM_DEBUG_LOG_MAX_CHARS         preview 最大长度（默认 2000）
  LLM_DEBUG_SAVE_RAW_RESPONSE     保存完整 upstream response / message content 文件（默认 true）
  LLM_DEBUG_RAW_RESPONSE_DIR      保存目录（默认 data/llm_calls）
  LLM_DEBUG_LOG_FULL_CONTENT      本地强调试，允许打印完整 content（默认 false）

安全：保存前递归 mask API key / Authorization / Bearer token；
      保存失败只记录 warning，不影响主流程。
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MAX_CHARS = 2000
_SENSITIVE_KEYS = (
    "api_key",
    "authorization",
    "proxy-authorization",
    "x-api-key",
)
_BEARER_RE = re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._\-]+)")


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def get_llm_debug_log_content() -> bool:
    """是否在 console 打印 message content preview。"""
    return _env_flag("LLM_DEBUG_LOG_CONTENT", default=False)


def get_llm_debug_log_full_content() -> bool:
    """是否在 console 打印完整 message content（仅本地强调试）。"""
    return _env_flag("LLM_DEBUG_LOG_FULL_CONTENT", default=False)


def get_llm_debug_save_raw_response() -> bool:
    """是否保存完整 upstream response / message content 到文件。"""
    return _env_flag("LLM_DEBUG_SAVE_RAW_RESPONSE", default=True)


def get_llm_debug_log_max_chars() -> int:
    """console preview 最大字符数。"""
    try:
        return max(1, int(os.getenv("LLM_DEBUG_LOG_MAX_CHARS", str(DEFAULT_MAX_CHARS))))
    except ValueError:
        return DEFAULT_MAX_CHARS


def get_llm_debug_raw_response_dir() -> Path:
    """raw response 保存目录。"""
    return Path(os.getenv("LLM_DEBUG_RAW_RESPONSE_DIR", "data/llm_calls"))


def mask_sensitive(data: Any) -> Any:
    """递归 mask API key / authorization / Bearer token。"""
    if isinstance(data, dict):
        return {
            str(k): ("[REDACTED]" if str(k).lower() in _SENSITIVE_KEYS else mask_sensitive(v))
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [mask_sensitive(v) for v in data]
    if isinstance(data, str):
        return _BEARER_RE.sub(r"\1[REDACTED]", data)
    return data


def save_raw_response(
    *,
    provider: str,
    request_id: str | None,
    task_name: str,
    raw_response: dict | None,
    content: str | None,
) -> tuple[str | None, str | None]:
    """保存完整 upstream response 与 message content；返回 (raw_path, content_path)。

    保存内容经过 mask_sensitive（不包含 API key）；失败只记录 warning。
    """
    if not get_llm_debug_save_raw_response():
        return None, None
    try:
        raw_dir = get_llm_debug_raw_response_dir()
        raw_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        safe_provider = re.sub(r"[^0-9A-Za-z_-]", "_", provider) or "unknown"
        safe_rid = re.sub(r"[^0-9A-Za-z_-]", "_", request_id or "") or "noreq"
        base = raw_dir / f"{ts}_{safe_provider}_{safe_rid}"
        raw_path = base.with_name(base.name + "_raw_response.json")
        content_path = base.with_name(base.name + "_message_content.txt")
        raw_path.write_text(
            json.dumps(mask_sensitive(raw_response or {}), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        content_path.write_text(content or "", encoding="utf-8")
        return str(raw_path), str(content_path)
    except Exception as exc:  # noqa: BLE001 - 保存失败不影响主流程
        logger.warning("LLM raw response 保存失败：%s", exc)
        return None, None
