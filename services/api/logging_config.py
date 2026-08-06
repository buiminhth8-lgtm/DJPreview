"""Python logging 配置（LOG_LEVEL 控制；默认 INFO，console 输出）。

LLM 调试相关 env（LLM_DEBUG_LOG_CONTENT / MAX_CHARS / SAVE_RAW_RESPONSE /
RAW_RESPONSE_DIR / LOG_FULL_CONTENT）统一委托给 packages.llm.llm_debug。
"""

from __future__ import annotations

import logging
import os

from packages.llm.llm_debug import (  # noqa: F401 - 兼容旧导入路径
    get_llm_debug_log_content,
    get_llm_debug_log_full_content,
    get_llm_debug_log_max_chars,
    get_llm_debug_raw_response_dir,
    get_llm_debug_save_raw_response,
)

_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_DEFAULT_LEVEL = "INFO"


def setup_logging(force: bool = False) -> None:
    """初始化根 logger。LOG_LEVEL 环境变量控制级别；未配置时保持默认。"""
    level_name = (os.getenv("LOG_LEVEL") or _DEFAULT_LEVEL).strip().upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format=_LOG_FORMAT, force=force)
