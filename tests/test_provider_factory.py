"""T32：LLM Provider 工厂测试。"""

import pytest

from packages.llm.base import LLMProvider
from packages.llm.deepseek_provider import DeepSeekProvider
from packages.llm.factory import get_llm_provider
from packages.llm.lmstudio_provider import LMStudioProvider
from packages.llm.mock_provider import MockProvider
from packages.llm.openai_compatible_provider import OpenAICompatibleProvider


def test_default_is_mock():
    assert isinstance(get_llm_provider(), MockProvider)


def test_mock_explicit():
    assert isinstance(get_llm_provider("mock"), MockProvider)


def test_deepseek_returns_provider(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    assert isinstance(get_llm_provider("deepseek"), DeepSeekProvider)


def test_lmstudio_returns_provider():
    provider = get_llm_provider("lmstudio")
    assert isinstance(provider, LMStudioProvider)
    assert isinstance(provider, LLMProvider)


def test_openai_compatible_returns_provider():
    provider = get_llm_provider("openai_compatible")
    assert isinstance(provider, OpenAICompatibleProvider)


def test_unknown_provider_raises_clear_error():
    with pytest.raises(ValueError, match="未知的 LLM_PROVIDER"):
        get_llm_provider("unknown_provider")
