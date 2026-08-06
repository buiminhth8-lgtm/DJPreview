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
    # 默认不落盘 raw response 文件，避免污染项目 data/llm_calls；需要时在具体测试里开启
    monkeypatch.setenv("LLM_DEBUG_SAVE_RAW_RESPONSE", kwargs.pop("save_raw", "false"))
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


# ---------- T35-Fix：raw response 调试 ----------

def _completion_with_meta(content: str, finish_reason: str = "stop", usage: dict | None = None) -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": "test-model",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": finish_reason}],
        "usage": usage or {"prompt_tokens": 12, "completion_tokens": 34, "total_tokens": 46},
    }


def test_save_raw_response_files(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_DEBUG_SAVE_RAW_RESPONSE", "true")
    monkeypatch.setenv("LLM_DEBUG_RAW_RESPONSE_DIR", str(tmp_path / "raw_dir"))
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=_completion_with_meta(json.dumps(_valid_spec_dict())))
    )
    provider = OpenAICompatibleProvider(
        api_key="sk-secret-123",
        base_url="http://localhost:9999/v1",
        model="test-model",
        transport=transport,
        call_logger=LLMCallLogger(base_dir=tmp_path / "data" / "projects"),
    )
    provider.generate_music_spec("测试")
    raw_files = list((tmp_path / "raw_dir").glob("*_raw_response.json"))
    content_files = list((tmp_path / "raw_dir").glob("*_message_content.txt"))
    assert raw_files
    assert content_files
    raw_data = json.loads(raw_files[0].read_text(encoding="utf-8"))
    assert raw_data["model"] == "test-model"
    assert raw_data["usage"]["total_tokens"] == 46
    assert content_files[0].read_text(encoding="utf-8")


def test_saved_raw_response_masks_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_DEBUG_SAVE_RAW_RESPONSE", "true")
    monkeypatch.setenv("LLM_DEBUG_RAW_RESPONSE_DIR", str(tmp_path / "raw_dir"))
    # upstream response 里带有 Authorization 头泄露的情况
    leaky = _completion_with_meta(json.dumps(_valid_spec_dict()))
    leaky["headers"] = {"authorization": "Bearer sk-secret-123", "x-api-key": "sk-secret-123"}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=leaky))
    provider = OpenAICompatibleProvider(
        api_key="sk-secret-123",
        base_url="http://localhost:9999/v1",
        model="m",
        transport=transport,
        call_logger=LLMCallLogger(base_dir=tmp_path / "data" / "projects"),
    )
    provider.generate_music_spec("测试")
    raw_files = list((tmp_path / "raw_dir").glob("*_raw_response.json"))
    assert raw_files
    content = raw_files[0].read_text(encoding="utf-8")
    assert "sk-secret-123" not in content
    assert "Authorization" not in content
    assert "[REDACTED]" in content


def test_finish_reason_length_adds_hint(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_DEBUG_SAVE_RAW_RESPONSE", "false")
    # finish_reason=length 且内容无效 JSON
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json=_completion_with_meta(
                '{"version": "0.1",', finish_reason="length",
                usage={"prompt_tokens": 12, "completion_tokens": 1800, "total_tokens": 1812},
            ),
        )
    )
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="http://localhost:9999/v1",
        model="m",
        transport=transport,
        call_logger=LLMCallLogger(base_dir=tmp_path / "data" / "projects"),
    )
    from packages.llm.structured_call import LLMOutputError

    with pytest.raises(LLMOutputError) as excinfo:
        provider.generate_music_spec("测试")
    debug_info = excinfo.value.debug_info or {}
    assert debug_info.get("finish_reason") == "length"
    assert "truncated" in (debug_info.get("hint") or "")


def test_finish_reason_stop_invalid_json_hint(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_DEBUG_SAVE_RAW_RESPONSE", "false")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json=_completion_with_meta("这不是 JSON，只是解释文字", finish_reason="stop"),
        )
    )
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="http://localhost:9999/v1",
        model="m",
        transport=transport,
        call_logger=LLMCallLogger(base_dir=tmp_path / "data" / "projects"),
    )
    from packages.llm.structured_call import LLMOutputError

    with pytest.raises(LLMOutputError) as excinfo:
        provider.generate_music_spec("测试")
    debug_info = excinfo.value.debug_info or {}
    assert debug_info.get("finish_reason") == "stop"
    assert "invalid JSON" in (debug_info.get("hint") or "")


def test_parse_failed_logs_contain_raw_response_path(tmp_path, monkeypatch, caplog):
    import logging

    monkeypatch.setenv("LLM_DEBUG_SAVE_RAW_RESPONSE", "true")
    monkeypatch.setenv("LLM_DEBUG_RAW_RESPONSE_DIR", str(tmp_path / "raw_dir"))
    monkeypatch.setenv("LLM_DEBUG_LOG_CONTENT", "false")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=_completion_with_meta("不是 JSON", finish_reason="stop"))
    )
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="http://localhost:9999/v1",
        model="m",
        transport=transport,
        call_logger=LLMCallLogger(base_dir=tmp_path / "data" / "projects"),
    )
    from packages.llm.structured_call import LLMOutputError

    with caplog.at_level(logging.INFO, logger="aimusic.llm"):
        with pytest.raises(LLMOutputError):
            provider.generate_music_spec("测试")
    joined = "\n".join(r.getMessage() for r in caplog.records)
    assert "raw_response_path" in joined
    assert "finish_reason" in joined
    assert "message_content_path" in joined


def test_llm_usage_tokens_in_call_log(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_DEBUG_SAVE_RAW_RESPONSE", "false")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=_completion_with_meta(json.dumps(_valid_spec_dict())))
    )
    provider = OpenAICompatibleProvider(
        api_key="sk-test",
        base_url="http://localhost:9999/v1",
        model="m",
        transport=transport,
        call_logger=LLMCallLogger(base_dir=tmp_path / "data" / "projects"),
    )
    provider.generate_music_spec("测试")
    logs = list(_log_dir(tmp_path).glob("*.json"))
    assert logs
    data = json.loads(logs[0].read_text(encoding="utf-8"))
    assert data["finish_reason"] == "stop"
    assert data["total_tokens"] == 46
    assert data["prompt_tokens"] == 12
    assert data["completion_tokens"] == 34
