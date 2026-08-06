"""OpenAICompatibleProvider —— 面向任意 OpenAI-compatible Chat Completions 服务的通用 Provider。

统一处理：
  - 配置读取（base_url / api_key / model / timeout，支持环境变量前缀）
  - `POST {base_url}/chat/completions` 调用
  - 结构化输出（JSON 提取 → Pydantic 校验 → 二次修复 → 重试）
  - LLM 调用日志（自动剔除 API Key / Authorization）

可复用给：DeepSeek、LM Studio、Ollama（OpenAI-compatible）、vLLM、LocalAI 等。

环境变量（以 `{PREFIX}` 前缀统一）：
  {PREFIX}_BASE_URL           base url，可带 /v1 结尾
  {PREFIX}_API_KEY            api key；本地服务允许占位值（如 lm-studio）
  {PREFIX}_MODEL              模型名
  {PREFIX}_TIMEOUT_SECONDS    HTTP 超时秒数
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


class OpenAICompatibleProvider(LLMProvider):
    """基于 OpenAI Chat Completions 的通用 Provider。

    子类通过类属性定制：
      name / env_prefix / display_name / default_base_url / default_model /
      default_timeout / require_api_key / default_api_key
    """

    name = "openai_compatible"
    env_prefix = "OPENAI_COMPATIBLE"
    display_name = "OpenAI-compatible"
    default_base_url = ""
    default_model = ""
    default_timeout = 120.0
    require_api_key = False
    default_api_key = ""

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
        self.api_key = (api_key if api_key is not None else os.getenv(f"{self.env_prefix}_API_KEY", "")).strip()
        if not self.api_key and self.require_api_key:
            raise LLMConfigurationError(
                f"{self.env_prefix}_API_KEY is not configured。请在 .env 中配置，"
                f"或将 LLM_PROVIDER 设为 mock。"
            )
        if not self.api_key:
            self.api_key = self.default_api_key
        self.base_url = (
            base_url or os.getenv(f"{self.env_prefix}_BASE_URL", "") or self.default_base_url
        ).rstrip("/")
        self.model = model or os.getenv(f"{self.env_prefix}_MODEL", "") or self.default_model
        timeout_value = timeout if timeout is not None else os.getenv(
            f"{self.env_prefix}_TIMEOUT_SECONDS", str(self.default_timeout)
        )
        self.timeout = float(timeout_value)
        self.prompt_registry = prompt_registry or PromptRegistry()
        self.call_logger = call_logger or LLMCallLogger()
        self._transport = transport

    # ---------- 高层业务方法 ----------

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

    # ---------- 结构化调用核心 ----------

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
            **self._request_extra(),
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
                **self._request_extra(),
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

    def _request_extra(self) -> dict:
        """请求体额外字段（子类可覆盖，如 response_format）。"""
        return {}

    # ---------- HTTP 层 ----------

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _chat_raw(self, request: dict) -> str:
        """发送 Chat Completions 请求，返回 message.content；失败抛 LLMAPIError。"""
        try:
            with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions", headers=self._headers(), json=request
                )
                resp.raise_for_status()
                data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as exc:
            raise LLMAPIError(
                f"{self.display_name} API 请求失败（HTTP {exc.response.status_code}）："
                f"{exc.response.text[:500]}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMAPIError(
                f"{self.display_name} API 请求超时（{self.timeout}s），请确认服务可达。"
            ) from exc
        except httpx.ConnectError as exc:
            raise LLMAPIError(f"{self.display_name} server not reachable：{exc}") from exc
        except httpx.HTTPError as exc:
            raise LLMAPIError(f"{self.display_name} API 网络错误：{exc}") from exc
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMAPIError(f"{self.display_name} API 返回格式异常（invalid response）：{exc}") from exc

    def fetch_models(self) -> list[str]:
        """调用 {base_url}/models（如服务支持）返回模型 id 列表；失败抛 LLMAPIError。"""
        try:
            with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
                resp = client.get(f"{self.base_url}/models", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
            items = data.get("data") or []
            return [m.get("id") for m in items if isinstance(m, dict) and m.get("id")]
        except httpx.HTTPStatusError as exc:
            raise LLMAPIError(
                f"{self.display_name} /models 请求失败（HTTP {exc.response.status_code}）："
                f"{exc.response.text[:500]}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMAPIError(
                f"{self.display_name} /models 请求超时（{self.timeout}s）。"
            ) from exc
        except httpx.ConnectError as exc:
            raise LLMAPIError(f"{self.display_name} server not reachable：{exc}") from exc
        except httpx.HTTPError as exc:
            raise LLMAPIError(f"{self.display_name} /models 网络错误：{exc}") from exc
        except (KeyError, ValueError) as exc:
            raise LLMAPIError(f"{self.display_name} /models 返回格式异常：{exc}") from exc
