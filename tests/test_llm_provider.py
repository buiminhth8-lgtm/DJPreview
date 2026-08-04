"""T11：LLM Provider 抽象与 MockProvider 兼容性测试。"""

import pytest
from fastapi.testclient import TestClient

from packages.llm.base import LLMProvider
from packages.llm.deepseek_provider import DeepSeekProvider
from packages.llm.mock_provider import MockProvider
from services.api.main import app
from services.api.schemas.music_edit_spec import MusicEditSpec
from services.api.schemas.music_spec import MusicSpec

client = TestClient(app)


def test_both_providers_satisfy_interface():
    assert isinstance(MockProvider(), LLMProvider)
    assert isinstance(DeepSeekProvider(api_key="sk-test"), LLMProvider)


def test_mock_provider_requires_no_api_key():
    provider = MockProvider()
    spec = provider.generate_music_spec("一首欢快的歌")
    assert spec.tonality.mode == "major"


def test_mock_generate_structured_returns_music_spec():
    provider = MockProvider()
    result = provider.generate_structured(
        system_prompt="",
        user_prompt="生成一段忧郁的钢琴曲",
        response_model=MusicSpec,
        task_name="generate_music_spec",
    )
    assert isinstance(result, MusicSpec)
    assert result.tonality.mode == "minor"


def test_mock_generate_structured_unsupported_model_raises():
    provider = MockProvider()
    with pytest.raises(ValueError, match="不支持"):
        provider.generate_structured(
            system_prompt="",
            user_prompt="更快",
            response_model=MusicEditSpec,
            task_name="generate_music_edit",
        )


def test_deepseek_missing_key_returns_unified_error(monkeypatch):
    """DeepSeek 配置缺失时返回统一 LLM_PROVIDER_ERROR，不影响 mock 回归。"""
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    resp = client.post("/api/v1/songs/generate", json={"prompt": "测试"})
    assert resp.status_code == 502
    body = resp.json()
    assert body["error_code"] == "LLM_PROVIDER_ERROR"
    assert "DEEPSEEK_API_KEY" in body["details"]["reason"]
