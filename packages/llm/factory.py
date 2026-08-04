"""LLM Provider 工厂。"""

from __future__ import annotations

import os

from packages.llm.base import LLMProvider
from packages.llm.deepseek_provider import DeepSeekProvider
from packages.llm.mock_provider import MockProvider


def get_llm_provider(provider_name: str | None = None) -> LLMProvider:
    """根据环境变量 LLM_PROVIDER 返回对应 Provider，默认 mock。

    支持值：mock、deepseek。
    """
    name = (provider_name or os.getenv("LLM_PROVIDER", "") or "mock").strip().lower()
    if name == "mock":
        return MockProvider()
    if name == "deepseek":
        return DeepSeekProvider()
    raise ValueError(f"未知的 LLM_PROVIDER：{name!r}（支持：mock、deepseek）")
