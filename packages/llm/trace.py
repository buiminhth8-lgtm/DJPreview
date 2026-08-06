"""请求级 trace 上下文：request_id 在中间件、路由与 LLM Provider 之间传递。

使用 contextvars 而非函数参数，避免大规模修改 Provider 签名。
"""

from __future__ import annotations

import logging
from contextvars import ContextVar

_request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# LLM / API 阶段日志专用 logger
api_logger = logging.getLogger("aimusic.api")
llm_logger = logging.getLogger("aimusic.llm")


def get_request_id() -> str:
    """返回当前请求的 request_id；无请求上下文时返回空字符串。"""
    return _request_id_var.get() or ""


def set_request_id(request_id: str) -> object:
    """设置当前 request_id，返回 token（供 reset 使用）。"""
    return _request_id_var.set(request_id)


def reset_request_id(token: object) -> None:
    """恢复 request_id 到之前状态。"""
    _request_id_var.reset(token)


def log_stage(logger: logging.Logger, stage: str, **fields) -> None:
    """输出带 request_id 的阶段日志。"""
    request_id = get_request_id()
    prefix = f"[request_id={request_id}]" if request_id else "[request_id=-]"
    parts = [f"{prefix} {stage}"]
    for key, value in fields.items():
        parts.append(f"{key}={value}")
    logger.info(" ".join(parts))
