"""T32/T33：LLM Provider 工厂测试。"""

import os

import pytest

from packages.llm.base import LLMProvider
from packages.llm.deepseek_provider import DeepSeekProvider
from packages.llm.factory import get_llm_provider
from packages.llm.lmstudio_provider import LMStudioProvider
from packages.llm.mock_provider import MockProvider
from packages.llm.openai_compatible_provider import OpenAICompatibleProvider
from packages.music_core.config.env_loader import load_env


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """测试前移除 LLM_PROVIDER / profile 相关变量，避免 conftest 的默认 mock 干扰 profile 加载测试。"""
    saved = dict(os.environ)
    for key in ("LLM_PROVIDER", "LLM_ENV_PROFILE", "LLM_ENV_FILE"):
        os.environ.pop(key, None)
    yield
    os.environ.clear()
    os.environ.update(saved)


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


def _write(tmp_path, name: str, content: str):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_mock_profile_loads_mock_provider(tmp_path):
    _write(tmp_path, ".mock.env", "LLM_PROVIDER=mock\n")
    load_env(profile="mock", env_dir=tmp_path)
    assert isinstance(get_llm_provider(), MockProvider)


def test_lmstudio_profile_loads_lmstudio_provider(tmp_path):
    _write(tmp_path, ".lmstudio.env", "LLM_PROVIDER=lmstudio\nLMSTUDIO_MODEL=local\n")
    load_env(profile="lmstudio", env_dir=tmp_path)
    provider = get_llm_provider()
    assert isinstance(provider, LMStudioProvider)
    assert provider.model == "local"


def test_deepseek_profile_loads_deepseek_provider(tmp_path):
    _write(tmp_path, ".deepseek.env", "LLM_PROVIDER=deepseek\nDEEPSEEK_API_KEY=sk-placeholder\n")
    load_env(profile="deepseek", env_dir=tmp_path)
    assert isinstance(get_llm_provider(), DeepSeekProvider)
