"""T32：OpenAICompatibleProvider 通用测试（mock httpx transport，不调用真实服务）。"""

import json

import httpx
import pytest

from packages.llm.call_logger import LLMCallLogger
from packages.llm.openai_compatible_provider import OpenAICompatibleProvider
from packages.llm.structured_call import LLMAPIError, LLMOutputError
from services.api.schemas.music_spec import MusicSpec
from tests.test_harmony_engine import build_spec


def _valid_spec_dict() -> dict:
    return build_spec().model_dump(mode="json")


def _completion(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}], "model": "test-model"}


def _provider(tmp_path, handler, **kwargs):
    transport = httpx.MockTransport(handler)
    return OpenAICompatibleProvider(
        api_key=kwargs.pop("api_key", "sk-test-123"),
        base_url=kwargs.pop("base_url", "http://localhost:9999/v1"),
        model=kwargs.pop("model", "test-model"),
        transport=transport,
        call_logger=LLMCallLogger(base_dir=tmp_path),
        **kwargs,
    )


def test_uses_base_url_without_double_slash():
    provider = OpenAICompatibleProvider(
        api_key="x",
        base_url="http://localhost:9999/v1/",
        model="m",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=_completion("{}"))),
    )
    assert provider.base_url == "http://localhost:9999/v1"


def test_generate_music_spec_success(tmp_path):
    provider = _provider(
        tmp_path,
        lambda request: httpx.Response(200, json=_completion(json.dumps(_valid_spec_dict()))),
    )
    spec = provider.generate_music_spec("生成一段忧郁空灵的钢琴配乐")
    assert spec.title
    assert len(spec.tracks) >= 5


def test_repair_fixes_invalid_json(tmp_path):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            content = "这不是 JSON，只是解释文字"
        else:
            content = json.dumps(_valid_spec_dict())
        return httpx.Response(200, json=_completion(content))

    provider = _provider(tmp_path, handler)
    spec = provider.generate_music_spec("测试")
    assert spec.title
    assert calls["n"] == 2


def test_http_500_converts_to_provider_error(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal server error")

    provider = _provider(tmp_path, handler)
    with pytest.raises(LLMAPIError, match="500"):
        provider.generate_structured(
            system_prompt="s",
            user_prompt="u",
            response_model=MusicSpec,
            task_name="generate_music_spec",
        )


def test_connection_error_message_clear(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused", request=request)

    provider = _provider(tmp_path, handler)
    with pytest.raises(LLMAPIError, match="not reachable"):
        provider.generate_structured(
            system_prompt="s",
            user_prompt="u",
            response_model=MusicSpec,
            task_name="generate_music_spec",
        )


def test_invalid_response_format_raises(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    provider = _provider(tmp_path, handler)
    with pytest.raises(LLMAPIError, match="invalid response"):
        provider.generate_structured(
            system_prompt="s",
            user_prompt="u",
            response_model=MusicSpec,
            task_name="generate_music_spec",
        )


def test_markdown_json_extracted_from_fence(tmp_path):
    content = '```json\n' + json.dumps(_valid_spec_dict()) + '\n```'
    provider = _provider(
        tmp_path,
        lambda request: httpx.Response(200, json=_completion(content)),
    )
    spec = provider.generate_music_spec("测试")
    assert spec.title


def test_music_spec_validation_failure_includes_path(tmp_path):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            content = json.dumps({"version": "0.1"})  # 缺 form/harmony/tracks
        else:
            content = json.dumps(_valid_spec_dict())
        return httpx.Response(200, json=_completion(content))

    provider = _provider(tmp_path, handler)
    spec = provider.generate_music_spec("测试")
    assert spec.title
    assert calls["n"] == 2


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
        project_id="song-keysafe",
    )
    log_dir = tmp_path / "song-keysafe" / "llm_calls"
    logs = list(log_dir.glob("*.json"))
    assert logs
    content = logs[0].read_text(encoding="utf-8")
    assert "sk-test-123" not in content
    assert "Authorization" not in content
    assert json.loads(content)["provider"] == "openai_compatible"


def test_fetch_models_returns_ids(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"id": "model-a"}, {"id": "model-b"}]})

    provider = _provider(tmp_path, handler)
    assert provider.fetch_models() == ["model-a", "model-b"]


def test_fetch_models_http_error(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    provider = _provider(tmp_path, handler)
    with pytest.raises(LLMAPIError, match="404"):
        provider.fetch_models()


def test_invalid_json_never_crashes_service(tmp_path):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json=_completion("还是错误输出"))

    provider = _provider(tmp_path, handler)
    with pytest.raises(LLMOutputError):
        provider.generate_structured(
            system_prompt="s",
            user_prompt="u",
            response_model=MusicSpec,
            task_name="generate_music_spec",
            retries=1,
        )
    assert calls["n"] == 2
