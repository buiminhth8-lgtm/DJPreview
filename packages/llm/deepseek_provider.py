"""DeepSeekProvider —— 通过 OpenAI-compatible Chat Completions 接口调用 DeepSeek。

复用 OpenAICompatibleProvider 的公共逻辑（配置 / HTTP / 结构化输出 / 日志），
仅保留 DeepSeek 的环境变量约定与默认值。
"""

from __future__ import annotations

from packages.llm.openai_compatible_provider import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek Provider，使用环境变量配置，不硬编码任何密钥。

    环境变量：
        DEEPSEEK_API_KEY            （必填）
        DEEPSEEK_BASE_URL           默认 https://api.deepseek.com
        DEEPSEEK_MODEL              默认 deepseek-chat
        DEEPSEEK_TIMEOUT_SECONDS    默认 60
    """

    name = "deepseek"
    env_prefix = "DEEPSEEK"
    display_name = "DeepSeek"
    default_base_url = "https://api.deepseek.com"
    default_model = "deepseek-chat"
    default_timeout = 60.0
    require_api_key = True

    def _request_extra(self) -> dict:
        return {"response_format": {"type": "json_object"}}
