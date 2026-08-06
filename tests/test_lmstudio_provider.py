"""T32：LMStudioProvider 测试（mock httpx transport，不调用真实 LM Studio）。"""

import json

import httpx
import pytest

from packages.llm.call_logger import LLMCallLogger
from packages.llm.lmstudio_provider import LMStudioProvider
from packages.llm.structured_call import LLMAPIError
from services.api.schemas.music_spec import MusicSpec
from tests.test_harmony_engine import build_spec


def _valid_spec_dict() -> dict:
    return build_spec().model_dump(mode="json")


def _completion(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}], "model": "local-model"}


def test_default_base_url_and_model():
    provider = LMStudioProvider(
        api_key="lm-studio",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=_completion("{}"))),
    )
    assert provider.name == "lmstudio"
    assert provider.base_url == "http://localhost:1234/v1"
    assert provider.model == "local-model"


def test_reads_env_vars(monkeypatch):
    monkeypatch.setenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:9999/v1")
    monkeypatch.setenv("LMSTUDIO_MODEL", "my-local-model")
    monkeypatch.setenv("LMSTUDIO_API_KEY", "lm-studio")
    monkeypatch.setenv("LMSTUDIO_TIMEOUT_SECONDS", "30")
    provider = LMStudioProvider(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=_completion("{}"))),
    )
    assert provider.base_url == "http://127.0.0.1:9999/v1"
    assert provider.model == "my-local-model"
    assert provider.timeout == 30.0


def test_no_api_key_uses_placeholder(monkeypatch):
    monkeypatch.delenv("LMSTUDIO_API_KEY", raising=False)
    provider = LMStudioProvider(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=_completion("{}"))),
    )
    assert provider.api_key == "lm-studio"


def test_generate_music_spec_success(tmp_path):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=_completion(json.dumps(_valid_spec_dict())))
    )
    provider = LMStudioProvider(
        base_url="http://localhost:1234/v1",
        model="local-model",
        transport=transport,
        call_logger=LLMCallLogger(base_dir=tmp_path),
    )
    spec = provider.generate_music_spec("生成一段忧郁空灵的钢琴配乐")
    assert spec.title
    assert len(spec.tracks) >= 5


def test_http_500_converts_to_provider_error(tmp_path):
    transport = httpx.MockTransport(lambda request: httpx.Response(500, text="model not loaded"))
    provider = LMStudioProvider(
        base_url="http://localhost:1234/v1",
        model="local-model",
        transport=transport,
        call_logger=LLMCallLogger(base_dir=tmp_path),
    )
    with pytest.raises(LLMAPIError, match="500"):
        provider.generate_music_spec("测试")


def test_connection_failure_clear_error(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused", request=request)

    provider = LMStudioProvider(
        base_url="http://localhost:1234/v1",
        model="local-model",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(LLMAPIError, match="not reachable"):
        provider.generate_music_spec("测试")


def test_fetch_models(tmp_path):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"data": [{"id": "local-model"}]})
    )
    provider = LMStudioProvider(
        base_url="http://localhost:1234/v1",
        model="local-model",
        transport=transport,
    )
    assert provider.fetch_models() == ["local-model"]


def test_generate_music_edit(tmp_path):
    from packages.llm.mock_provider import MockProvider

    edit_dict = MockProvider().generate_music_edit("更快", build_spec()).model_dump(mode="json")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=_completion(json.dumps(edit_dict)))
    )
    provider = LMStudioProvider(
        base_url="http://localhost:1234/v1",
        model="local-model",
        transport=transport,
        call_logger=LLMCallLogger(base_dir=tmp_path),
    )
    edit = provider.generate_music_edit("更快", build_spec())
    assert edit.instruction == "更快"
    assert edit.target.scope == "partial"
