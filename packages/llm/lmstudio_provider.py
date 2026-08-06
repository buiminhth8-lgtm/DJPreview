"""LMStudioProvider —— 通过 LM Studio 本地 OpenAI-compatible API 调用本地模型。

复用 OpenAICompatibleProvider 的公共逻辑；LM Studio 不强制真实 API Key
（允许占位值，如 `lm-studio`），用于本地验证真实 LLM 链路。
"""

from __future__ import annotations

from packages.llm.openai_compatible_provider import OpenAICompatibleProvider


class LMStudioProvider(OpenAICompatibleProvider):
    """LM Studio 本地 Provider。

    环境变量：
        LMSTUDIO_BASE_URL           默认 http://localhost:1234/v1
        LMSTUDIO_API_KEY            默认 lm-studio（占位，非必填真实密钥）
        LMSTUDIO_MODEL              默认 local-model（须与 LM Studio 已加载模型一致）
        LMSTUDIO_TIMEOUT_SECONDS    默认 120
    """

    name = "lmstudio"
    env_prefix = "LMSTUDIO"
    display_name = "LM Studio"
    default_base_url = "http://localhost:1234/v1"
    default_model = "local-model"
    default_timeout = 120.0
    require_api_key = False
    default_api_key = "lm-studio"
