"""LLM Provider 统一抽象接口。"""

from abc import ABC, abstractmethod

from services.api.schemas.music_edit_spec import MusicEditSpec
from services.api.schemas.music_spec import MusicSpec


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
