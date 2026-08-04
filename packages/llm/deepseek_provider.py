"""DeepSeekProvider —— 通过 OpenAI-compatible Chat Completions 接口调用 DeepSeek。"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx
from pydantic import ValidationError

from packages.llm.base import LLMProvider
from services.api.schemas.music_edit_spec import MusicEditSpec
from services.api.schemas.music_spec import MusicSpec

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PLANNER_PROMPT_PATH = _PROJECT_ROOT / "prompts" / "music_planner.md"

_FALLBACK_SYSTEM_PROMPT = (
    "你是资深音乐制作人。请把用户的自然语言描述转换为符合 MusicSpec v0.1 协议的 JSON，"
    "只返回 JSON，不要 Markdown，不要解释。必须包含 form、harmony、tracks。"
)


class DeepSeekProvider(LLMProvider):
    """DeepSeek Provider，使用环境变量配置，不硬编码任何密钥。"""

    name = "deepseek"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = (base_url or os.getenv("DEEPSEEK_BASE_URL", "") or "https://api.deepseek.com").rstrip("/")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "") or "deepseek-chat"
        self.timeout = timeout
        if not self.api_key:
            raise ValueError(
                "未检测到 DEEPSEEK_API_KEY，无法调用 DeepSeek。"
                "请在 .env 中配置 DEEPSEEK_API_KEY，或将 LLM_PROVIDER 设为 mock 使用 MockProvider。"
            )

    def generate_music_spec(self, prompt: str) -> MusicSpec:
        system_prompt = self._load_system_prompt()
        raw = self._chat(system_prompt, prompt)
        return self._parse_music_spec(raw)

    def generate_music_edit(self, instruction: str, current_spec: MusicSpec) -> MusicEditSpec:
        system_prompt = (
            "你是资深音乐制作人。请根据用户的修改指令，把当前 MusicSpec v0.1 转换为 MusicEditSpec v0.1 JSON。"
            "只返回 JSON，不要 Markdown，不要解释。"
        )
        user_prompt = (
            f"修改指令：{instruction}\n\n"
            f"当前 MusicSpec：\n{current_spec.model_dump_json(indent=2)}"
        )
        raw = self._chat(system_prompt, user_prompt)
        return self._parse_music_edit_spec(raw)

    def _chat(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
        }
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"DeepSeek API 请求失败（HTTP {exc.response.status_code}）：{exc.response.text[:500]}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise RuntimeError("DeepSeek API 请求超时，请稍后重试。") from exc
        except (KeyError, IndexError, ValueError) as exc:
            raise RuntimeError(f"DeepSeek API 返回格式异常：{exc}") from exc

    def _parse_music_spec(self, raw: str) -> MusicSpec:
        data = self._parse_json(raw)
        try:
            return MusicSpec.model_validate(data)
        except ValidationError as exc:
            raise ValueError(f"模型输出不符合 MusicSpec v0.1 协议：{exc}") from exc

    def _parse_music_edit_spec(self, raw: str) -> MusicEditSpec:
        data = self._parse_json(raw)
        try:
            return MusicEditSpec.model_validate(data)
        except ValidationError as exc:
            raise ValueError(f"模型输出不符合 MusicEditSpec v0.1 协议：{exc}") from exc

    @staticmethod
    def _parse_json(raw: str) -> dict:
        text = raw.strip()
        # 防御性剥离 Markdown 代码块
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("模型输出不是合法 JSON，解析失败。可改用 MockProvider 或调整提示词。") from exc
        if not isinstance(data, dict):
            raise ValueError("模型输出 JSON 不是对象，解析失败。")
        return data

    def _load_system_prompt(self) -> str:
        try:
            return _PLANNER_PROMPT_PATH.read_text(encoding="utf-8")
        except OSError:
            return _FALLBACK_SYSTEM_PROMPT
