"""LLM Provider 统一抽象接口。"""

from abc import ABC, abstractmethod
from typing import Type, TypeVar

from pydantic import BaseModel

from services.api.schemas.music_edit_spec import MusicEditSpec
from services.api.schemas.music_spec import MusicSpec

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """所有 LLM Provider 必须实现的统一接口。

    后续扩展 OpenAIProvider、OllamaProvider、LocalModelProvider 时，
    只需实现本接口并注册到 factory，即可被业务代码复用。
    """

    name: str = "base"

    @abstractmethod
    def generate_music_spec(self, prompt: str) -> MusicSpec:
        """根据自然语言描述生成 MusicSpec。"""

    @abstractmethod
    def generate_music_edit(self, instruction: str, current_spec: MusicSpec) -> MusicEditSpec:
        """根据修改指令与当前 MusicSpec 生成 MusicEditSpec。"""

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
        """统一结构化调用入口：system + user → JSON → Pydantic 校验。

        子类应重写：DeepSeekProvider 走真实 Chat Completions + 修复 + 日志，
        MockProvider 走规则生成，不发起网络请求。
        """
        raise NotImplementedError("LLMProvider.generate_structured 未实现")
