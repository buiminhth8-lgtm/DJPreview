"""Python logging 配置（LOG_LEVEL 控制；默认 INFO，console 输出）。"""

from __future__ import annotations

import logging
import os

_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_DEFAULT_LEVEL = "INFO"


def setup_logging(force: bool = False) -> None:
    """初始化根 logger。LOG_LEVEL 环境变量控制级别；未配置时保持默认。"""
    level_name = (os.getenv("LOG_LEVEL") or _DEFAULT_LEVEL).strip().upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format=_LOG_FORMAT, force=force)


def get_llm_debug_log_content() -> bool:
    """是否记录 LLM raw response preview（LLM_DEBUG_LOG_CONTENT=true）。"""
    raw = (os.getenv("LLM_DEBUG_LOG_CONTENT") or "false").strip().lower()
    return raw in ("1", "true", "yes", "on")
