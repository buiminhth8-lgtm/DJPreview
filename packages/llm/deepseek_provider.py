"""DeepSeekProvider —— 通过 OpenAI-compatible Chat Completions 接口调用 DeepSeek。

核心能力：Prompt Registry 管理 prompt、统一 generate_structured 结构化调用、
JSON 提取 + Pydantic 校验 + 二次修复、LLM 调用日志（不含 API Key）。
"""

from __future__ import annotations

import json
import os
import time
from typing import Type

import httpx

from packages.llm.base import LLMProvider, T
from packages.llm.call_logger import LLMCallLogger
from packages.llm.prompt_registry import PromptRegistry
from packages.llm.structured_call import (
    LLMAPIError,
    LLMConfigurationError,
    LLMOutputError,
    parse_structured_response,
)
from services.api.schemas.music_edit_spec import MusicEditSpec
from services.api.schemas.music_spec import MusicSpec


class DeepSeekProvider(LLMProvider):
    """DeepSeek Provider，使用环境变量配置，不硬编码任何密钥。

    环境变量：
        DEEPSEEK_API_KEY            （必填）
        DEEPSEEK_BASE_URL           默认 https://api.deepseek.com
        DEEPSEEK_MODEL              默认 deepseek-chat
        DEEPSEEK_TIMEOUT_SECONDS    默认 60
    """

    name = "deepseek"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        transport: httpx.BaseTransport | None = None,
        prompt_registry: PromptRegistry | None = None,
        call_logger: LLMCallLogger | None = None,
    ) -> None:
        self.api_key = (api_key or os.getenv("DEEPSEEK_API_KEY", "") or "").strip()
        if not self.api_key:
            raise LLMConfigurationError(
                "DEEPSEEK_API_KEY is not configured。请在 .env 中配置，或将 LLM_PROVIDER 设为 mock。"
            )
        self.base_url = (
            base_url or os.getenv("DEEPSEEK_BASE_URL", "") or "https://api.deepseek.com"
        ).rstrip("/")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "") or "deepseek-chat"
        timeout_value = timeout if timeout is not None else os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "60")
        self.timeout = float(timeout_value)
        self.prompt_registry = prompt_registry or PromptRegistry()
        self.call_logger = call_logger or LLMCallLogger()
        self._transport = transport

    def generate_music_spec(self, prompt: str) -> MusicSpec:
        """使用 Prompt Registry 的 music_spec_generator 生成 MusicSpec。"""
        system_prompt = self.prompt_registry.get_prompt("music_spec_generator")
        return self.generate_structured(
            system_prompt=system_prompt,
            user_prompt=prompt,
            response_model=MusicSpec,
            task_name="generate_music_spec",
        )

    def generate_music_edit(
        self,
        instruction: str,
        current_spec: MusicSpec,
        project_id: str | None = None,
    ) -> MusicEditSpec:
        """使用 Prompt Registry 的 music_editor 生成 MusicEditSpec。"""
        system_prompt = self.prompt_registry.get_prompt("music_editor")
        user_prompt = self.prompt_registry.render_prompt(
            "music_editor",
            {
                "music_spec": current_spec.model_dump_json(indent=2),
                "instruction": instruction,
            },
        )
        return self.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=MusicEditSpec,
            task_name="generate_music_edit",
            project_id=project_id,
        )

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        task_name: str,
        project_id: str | None = None,
        retries: int = 2,
    ) -> T:
        """统一结构化调用：Chat Completions → JSON 提取 → Pydantic 校验 → 修复。"""
        request = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
        }

        started = time.monotonic()
        try:
            raw = self._chat_raw(request)
        except Exception:
            latency_ms = int((time.monotonic() - started) * 1000)
            self.call_logger.log_call(
                project_id=project_id,
                task_name=task_name,
                provider=self.name,
                model=self.model,
                request=request,
                error="API 调用失败",
                latency_ms=latency_ms,
            )
            raise
        latency_ms = int((time.monotonic() - started) * 1000)

        def repair(raw_output: str, error_text: str) -> str:
            repair_system = self.prompt_registry.get_prompt("json_repair")
            repair_user = (
                f"任务：{task_name}\n\n"
                f"原始模型输出：\n{raw_output}\n\n"
                f"校验错误：\n{error_text}\n\n"
                f"目标 JSON schema 简要说明：\n{json.dumps(response_model.model_json_schema(), ensure_ascii=False)}"
            )
            repair_request = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": repair_system},
                    {"role": "user", "content": repair_user},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            }
            repaired = self._chat_raw(repair_request)
            self.call_logger.log_call(
                project_id=project_id,
                task_name=f"{task_name}/repair",
                provider=self.name,
                model=self.model,
                request=repair_request,
                response={"content": repaired[:2000]},
                latency_ms=None,
            )
            return repaired

        try:
            result = parse_structured_response(
                response_model,
                raw,
                repair_fn=repair,
                retries=retries,
                task_name=task_name,
            )
        except LLMOutputError as exc:
            self.call_logger.log_call(
                project_id=project_id,
                task_name=task_name,
                provider=self.name,
                model=self.model,
                request=request,
                response={"content": raw[:2000]},
                error=str(exc),
                latency_ms=latency_ms,
            )
            raise

        self.call_logger.log_call(
            project_id=project_id,
            task_name=task_name,
            provider=self.name,
            model=self.model,
            request=request,
            response={"content": raw[:2000]},
            parsed=result.model_dump(mode="json"),
            latency_ms=latency_ms,
        )
        return result

    def _chat_raw(self, request: dict) -> str:
        """发送 Chat Completions 请求，返回 message.content；失败抛 LLMAPIError。"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
                resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=request)
                resp.raise_for_status()
                data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as exc:
            raise LLMAPIError(
                f"DeepSeek API 请求失败（HTTP {exc.response.status_code}）：{exc.response.text[:500]}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMAPIError("DeepSeek API 请求超时，请稍后重试。") from exc
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMAPIError(f"DeepSeek API 返回格式异常：{exc}") from exc
