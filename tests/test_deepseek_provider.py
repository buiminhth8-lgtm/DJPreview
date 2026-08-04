"""T11：DeepSeekProvider 测试（mock httpx transport，不调用真实 API）。"""

import json

import httpx
import pytest

from packages.llm.call_logger import LLMCallLogger
from packages.llm.deepseek_provider import DeepSeekProvider
from packages.llm.structured_call import LLMConfigurationError, LLMOutputError
from services.api.schemas.music_spec import MusicSpec
from tests.test_harmony_engine import build_spec


def _valid_spec_dict() -> dict:
    return build_spec().model_dump(mode="json")


def _valid_edit_dict() -> dict:
    from packages.llm.mock_provider import MockProvider

    return MockProvider().generate_music_edit("更快", build_spec()).model_dump(mode="json")


def _completion(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}], "model": "deepseek-chat"}


def _provider(tmp_path, handler, **kwargs):
    transport = httpx.MockTransport(handler)
    return DeepSeekProvider(
        api_key=kwargs.pop("api_key", "sk-test-123"),
        transport=transport,
        call_logger=LLMCallLogger(base_dir=tmp_path),
        **kwargs,
    )


def test_generate_music_spec_success(tmp_path):
    provider = _provider(
        tmp_path,
        lambda request: httpx.Response(200, json=_completion(json.dumps(_valid_spec_dict()))),
    )
    spec = provider.generate_music_spec("生成一段忧郁空灵的钢琴配乐")
    assert spec.title
    assert len(spec.tracks) >= 5
    assert spec.tonality.key == "D"


def test_generate_music_edit_success(tmp_path):
    provider = _provider(
        tmp_path,
        lambda request: httpx.Response(200, json=_completion(json.dumps(_valid_edit_dict()))),
    )
    edit = provider.generate_music_edit("更快", build_spec(), project_id="song-1")
    assert edit.instruction == "更快"
    assert edit.target.scope == "partial"


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


def test_repair_fixes_schema_mismatch(tmp_path):
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


def test_repair_still_fails_raises_output_error(tmp_path):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json=_completion("还是错误输出"))

    provider = _provider(tmp_path, handler)
    with pytest.raises(LLMOutputError) as excinfo:
        provider.generate_structured(
            system_prompt="system",
            user_prompt="测试",
            response_model=MusicSpec,
            task_name="generate_music_spec",
            retries=2,
        )
    assert excinfo.value.task_name == "generate_music_spec"
    assert calls["n"] == 3  # 初次 + 2 次修复


def test_missing_api_key_raises_config_error(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(LLMConfigurationError, match="DEEPSEEK_API_KEY"):
        DeepSeekProvider()


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
    assert json.loads(content)["provider"] == "deepseek"
