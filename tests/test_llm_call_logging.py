"""T35：LLM 调用日志增强测试（request_id / 字段 / API key 不泄露）。"""

import json

import httpx
import pytest

from packages.llm.call_logger import LLMCallLogger
from packages.llm.openai_compatible_provider import OpenAICompatibleProvider
from packages.llm.trace import reset_request_id, set_request_id
from tests.test_harmony_engine import build_spec


def _valid_spec_dict() -> dict:
    return build_spec().model_dump(mode="json")


def _completion(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def _log_dir(tmp_path):
    # 无 project_id 时日志落在 base_dir.parent/llm_calls；用独立目录隔离每个测试
    return tmp_path / "data" / "llm_calls"


def _provider(tmp_path, monkeypatch, **kwargs):
    monkeypatch.setenv("LLM_DEBUG_LOG_CONTENT", kwargs.pop("debug_content", "false"))
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=_completion(json.dumps(_valid_spec_dict())))
    )
    return OpenAICompatibleProvider(
        api_key=kwargs.pop("api_key", "sk-secret-123"),
        base_url="http://localhost:9999/v1",
        model="test-model",
        transport=transport,
        call_logger=LLMCallLogger(base_dir=tmp_path / "data" / "projects"),
    )


def test_call_log_contains_request_id(tmp_path, monkeypatch):
    provider = _provider(tmp_path, monkeypatch)
    token = set_request_id("req-abc-123")
    try:
        provider.generate_music_spec("生成一段忧郁空灵的钢琴配乐")
    finally:
        reset_request_id(token)

    logs = list(_log_dir(tmp_path).glob("*.json"))
    assert logs
    data = json.loads(logs[0].read_text(encoding="utf-8"))
    assert data["request_id"] == "req-abc-123"
    assert data["provider"] == "openai_compatible"
    assert data["json_parse"] == "success"
    assert data["model"] == "test-model"


def test_filename_includes_provider_and_request_id(tmp_path):
    logger = LLMCallLogger(base_dir=tmp_path / "data" / "projects")
    path = logger.log_call(
        project_id=None,
        task_name="generate_music_spec",
        provider="gemini",
        model="gemini-3.5-flash",
        request={"model": "gemini-3.5-flash", "messages_count": 2},
        request_id="req-gemini-1",
    )
    assert path is not None
    assert "gemini" in path.name
    assert "req-gemini-1" in path.name


def test_log_never_contains_api_key_or_authorization(tmp_path):
    logger = LLMCallLogger(base_dir=tmp_path / "data" / "projects")
    path = logger.log_call(
        project_id=None,
        task_name="generate_music_spec",
        provider="deepseek",
        model="deepseek-chat",
        request={"api_key": "sk-secret", "authorization": "Bearer sk-secret", "messages": []},
        response={"echo": "ok"},
        request_id="req-safe",
    )
    assert path is not None
    content = path.read_text(encoding="utf-8")
    assert "sk-secret" not in content
    assert "Authorization" not in content
    assert "api_key" not in content


def test_debug_log_content_disabled_hides_raw(tmp_path, monkeypatch):
    provider = _provider(tmp_path, monkeypatch)
    provider.generate_music_spec("测试")
    logs = list(_log_dir(tmp_path).glob("*.json"))
    assert logs
    data = json.loads(logs[0].read_text(encoding="utf-8"))
    assert data.get("raw_response_preview") is None
    # 默认不应保存完整 prompt
    req = data["request"]
    assert req.get("debug_content_disabled") is True


def test_debug_log_content_enabled_keeps_preview(tmp_path, monkeypatch):
    provider = _provider(tmp_path, monkeypatch, debug_content="true")
    provider.generate_music_spec("测试")
    logs = list(_log_dir(tmp_path).glob("*.json"))
    assert logs
    data = json.loads(logs[0].read_text(encoding="utf-8"))
    assert data.get("raw_response_preview") is not None
    assert len(data["raw_response_preview"]) <= 2000
