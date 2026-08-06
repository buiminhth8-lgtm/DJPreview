"""Music Planner —— 自然语言 → MusicSpec 的编排入口。"""

from __future__ import annotations

from packages.llm.factory import get_llm_provider
from packages.music_core.normalization.instrument_normalizer import normalize_music_spec
from packages.music_core.validation.spec_validator import validate_music_spec
from services.api.schemas.music_spec import MusicSpec


def generate_music_spec_from_prompt(prompt: str) -> MusicSpec:
    """根据一句话描述生成并校验 MusicSpec。

    流程：获取 LLMProvider → 生成 MusicSpec → 乐器名 normalize → 语义校验 → 返回。
    """
    provider = get_llm_provider()
    spec = provider.generate_music_spec(prompt)
    spec, _ = normalize_music_spec(spec)
    return validate_music_spec(spec)
