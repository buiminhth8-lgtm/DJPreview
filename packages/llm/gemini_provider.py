"""GeminiProvider —— 通过 Gemini OpenAI-compatible endpoint 调用 Gemini API。

复用 OpenAICompatibleProvider 的公共逻辑（配置 / HTTP / 结构化输出 / 日志），
并追加 Gemini 专属参数：temperature / max_tokens / reasoning_effort / response_format。

Gemini OpenAI compatibility 仍处 Beta，系统会尽量发送结构化输出；若
response_format 不被接受（如 HTTP 400），自动 fallback 到普通 chat completions，
再走现有 JSON extract / repair / validation。
"""

from __future__ import annotations

import os

from packages.llm.openai_compatible_provider import OpenAICompatibleProvider
from packages.llm.structured_call import LLMAPIError

# Gemini OpenAI-compatible 官方 base URL（尾部带斜杠，拼接时会去重避免双斜杠）
DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"

_ALLOWED_REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high")


class GeminiProvider(OpenAICompatibleProvider):
    """Gemini Provider，使用环境变量配置，不硬编码任何密钥。

    环境变量：
        GEMINI_API_KEY                （必填）
        GEMINI_BASE_URL               默认 https://generativelanguage.googleapis.com/v1beta/openai/
        GEMINI_MODEL                  默认 gemini-3.5-flash
        GEMINI_TIMEOUT_SECONDS        默认 120
        GEMINI_TEMPERATURE            默认 0.2
        GEMINI_MAX_TOKENS             默认 1800
        GEMINI_REASONING_EFFORT       可选：none / minimal / low / medium / high（为空则不发送）
        GEMINI_USE_RESPONSE_FORMAT    默认 true（尝试结构化输出，失败自动 fallback）
    """

    name = "gemini"
    env_prefix = "GEMINI"
    display_name = "Gemini"
    default_base_url = DEFAULT_GEMINI_BASE_URL
    default_model = DEFAULT_GEMINI_MODEL
    default_timeout = 120.0
    require_api_key = True

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        transport=None,
        prompt_registry=None,
        call_logger=None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_effort: str | None = None,
        use_response_format: bool | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=timeout,
            transport=transport,
            prompt_registry=prompt_registry,
            call_logger=call_logger,
        )
        self.temperature = float(
            temperature if temperature is not None else os.getenv("GEMINI_TEMPERATURE", "0.2")
        )
        self.max_tokens = int(
            max_tokens if max_tokens is not None else os.getenv("GEMINI_MAX_TOKENS", "1800")
        )
        if reasoning_effort is not None:
            self.reasoning_effort = str(reasoning_effort).strip().lower()
        else:
            self.reasoning_effort = os.getenv("GEMINI_REASONING_EFFORT", "").strip().lower()
        if use_response_format is not None:
            self.use_response_format = bool(use_response_format)
        else:
            raw = os.getenv("GEMINI_USE_RESPONSE_FORMAT", "true").strip().lower()
            self.use_response_format = raw in ("1", "true", "yes", "on")

    # ---------- 请求体构建 ----------

    def _request_extra(self) -> dict:
        """追加 Gemini 专属请求字段（temperature / max_tokens / reasoning_effort / response_format）。"""
        extra: dict = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.reasoning_effort:
            if self.reasoning_effort in _ALLOWED_REASONING_EFFORTS:
                extra["reasoning_effort"] = self.reasoning_effort
            else:
                extra["reasoning_effort"] = "low"
        if self.use_response_format:
            extra["response_format"] = {"type": "json_object"}
        return extra

    # ---------- HTTP：response_format fallback ----------

    def _chat_raw(self, request: dict) -> str:
        """发送 chat/completions；若启用 response_format 且被服务拒绝（HTTP 4xx），
        fallback 到去掉 response_format 的普通 chat completions。"""
        if self.use_response_format and request.get("response_format"):
            fallback_request = dict(request)
            fallback_request.pop("response_format", None)
            try:
                return super()._chat_raw(request)
            except LLMAPIError as exc:
                if exc.status_code not in (400, 422, 404):
                    raise
                return super()._chat_raw(fallback_request)
        return super()._chat_raw(request)
