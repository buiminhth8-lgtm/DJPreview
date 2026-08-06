"""T34：GeminiProvider 测试（mock httpx transport，不调用真实 Gemini API）。"""

import json

import httpx
import pytest

from packages.llm.call_logger import LLMCallLogger
from packages.llm.gemini_provider import GeminiProvider
from packages.llm.structured_call import LLMAPIError, LLMConfigurationError
from services.api.schemas.music_spec import MusicSpec
from tests.test_harmony_engine import build_spec


def _valid_spec_dict() -> dict:
    return build_spec().model_dump(mode="json")


def _completion(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}], "model": "gemini-3.5-flash"}


def _provider(tmp_path, handler, **kwargs):
    return GeminiProvider(
        api_key=kwargs.pop("api_key", "sk-test-123"),
        base_url=kwargs.pop("base_url", "https://generativelanguage.googleapis.com/v1beta/openai/"),
        model=kwargs.pop("model", "gemini-3.5-flash"),
        transport=httpx.MockTransport(handler),
        call_logger=LLMCallLogger(base_dir=tmp_path),
        **kwargs,
    )


def test_default_base_url_and_model():
    provider = GeminiProvider(
        api_key="sk-test",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=_completion("{}"))),
    )
    assert provider.name == "gemini"
    assert provider.base_url == "https://generativelanguage.googleapis.com/v1beta/openai"
    assert provider.model == "gemini-3.5-flash"


def test_base_url_no_double_slash(tmp_path):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=_completion(json.dumps(_valid_spec_dict())))

    provider = _provider(tmp_path, handler)
    provider.generate_music_spec("测试")
    assert "//chat/completions" not in captured["url"]
    assert captured["url"].endswith("/openai/chat/completions")


def test_generate_music_spec_success(tmp_path):
    provider = _provider(
        tmp_path,
        lambda request: httpx.Response(200, json=_completion(json.dumps(_valid_spec_dict()))),
    )
    spec = provider.generate_music_spec("生成一段忧郁空灵的钢琴配乐")
    assert spec.title
    assert len(spec.tracks) >= 5


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(LLMConfigurationError, match="GEMINI_API_KEY"):
        GeminiProvider(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=_completion("{}"))))


def test_auth_header_bearer(tmp_path):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json=_completion(json.dumps(_valid_spec_dict())))

    provider = _provider(tmp_path, handler)
    provider.generate_music_spec("测试")
    assert captured["auth"] == "Bearer sk-test-123"


def test_log_does_not_contain_api_key(tmp_path):
    provider = _provider(
        tmp_path,
        lambda request: httpx.Response(200, json=_completion(json.dumps(_valid_spec_dict()))),
    )
    provider.generate_structured(
        system_prompt="system",
        user_prompt="测试",
        response_model=MusicSpec,
        task_name="generate_music_spec",
        project_id="song-gemini-keysafe",
    )
    logs = list((tmp_path / "song-gemini-keysafe" / "llm_calls").glob("*.json"))
    assert logs
    content = logs[0].read_text(encoding="utf-8")
    assert "sk-test-123" not in content
    assert "Authorization" not in content
    assert json.loads(content)["provider"] == "gemini"


def test_reasoning_effort_in_body(tmp_path):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_completion(json.dumps(_valid_spec_dict())))

    provider = _provider(tmp_path, handler, reasoning_effort="low", use_response_format=True)
    provider.generate_music_spec("测试")
    assert captured["body"]["reasoning_effort"] == "low"
    assert captured["body"]["response_format"] == {"type": "json_object"}
    assert captured["body"]["temperature"] == 0.2
    assert captured["body"]["max_tokens"] == 1800


def test_reasoning_effort_empty_not_sent(tmp_path):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_completion(json.dumps(_valid_spec_dict())))

    provider = _provider(tmp_path, handler, reasoning_effort="", use_response_format=False)
    provider.generate_music_spec("测试")
    assert "reasoning_effort" not in captured["body"]
    assert "response_format" not in captured["body"]


def test_response_format_fallback(tmp_path):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        body = json.loads(request.content)
        if "response_format" in body:
            return httpx.Response(400, text="response_format not supported")
        return httpx.Response(200, json=_completion(json.dumps(_valid_spec_dict())))

    provider = _provider(tmp_path, handler, use_response_format=True)
    spec = provider.generate_music_spec("测试")
    assert spec.title
    assert calls["n"] == 2  # 先带 response_format，失败后 fallback


def test_http_500_converts_to_provider_error(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal error")

    provider = _provider(tmp_path, handler)
    with pytest.raises(LLMAPIError, match="500"):
        provider.generate_music_spec("测试")


def test_connection_failure_clear_error(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused", request=request)

    provider = _provider(tmp_path, handler)
    with pytest.raises(LLMAPIError, match="not reachable"):
        provider.generate_music_spec("测试")


def test_invalid_json_never_crashes(tmp_path):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json=_completion("还是错误输出"))

    provider = _provider(tmp_path, handler)
    from packages.llm.structured_call import LLMOutputError

    with pytest.raises(LLMOutputError):
        provider.generate_music_spec("测试")
    assert calls["n"] >= 2  # 初次 + 修复


def test_fetch_models(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"id": "gemini-3.5-flash"}, {"id": "gemini-2.5-flash"}]})

    provider = _provider(tmp_path, handler)
    assert provider.fetch_models() == ["gemini-3.5-flash", "gemini-2.5-flash"]


def test_retrieve_model(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "gemini-3.5-flash", "object": "model"})

    provider = _provider(tmp_path, handler)
    detail = provider.retrieve_model("gemini-3.5-flash")
    assert detail["id"] == "gemini-3.5-flash"


def test_retrieve_model_http_error(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="model not found")

    provider = _provider(tmp_path, handler)
    with pytest.raises(LLMAPIError, match="404"):
        provider.retrieve_model("nope")
