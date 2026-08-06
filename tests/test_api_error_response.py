"""T35：统一 API 错误结构（success / request_id / error.code / stage）测试。"""

import pytest
from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)

def _assert_error_structure(body: dict, code: str):
    assert body["success"] is False
    assert body["request_id"]
    assert body["error_code"] == code
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    assert body["error"]["stage"]
    assert isinstance(body["error"]["status_code"], int)
    assert isinstance(body["error"]["details"], dict)


def test_project_not_found_error_structure():
    resp = client.get("/api/v1/songs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    body = resp.json()
    _assert_error_structure(body, "PROJECT_NOT_FOUND")


def test_llm_provider_error_has_stage_llm_call(monkeypatch):
    """DeepSeek 缺 key 时报 LLM_PROVIDER_ERROR，stage=provider_selection。"""
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    resp = client.post("/api/v1/songs/generate", json={"prompt": "测试"})
    assert resp.status_code == 502
    body = resp.json()
    _assert_error_structure(body, "LLM_PROVIDER_ERROR")
    assert body["error"]["stage"] in ("provider_selection", "llm_call")


def test_invalid_request_stage():
    resp = client.get("/api/v1/songs/not-a-uuid")
    assert resp.status_code == 400
    body = resp.json()
    _assert_error_structure(body, "INVALID_REQUEST")
    assert body["error"]["stage"] == "request_validation"


def test_internal_error_structure():
    """未知异常应返回 INTERNAL_ERROR + request_id（不返回 traceback）。"""
    resp = client.get("/api/v1/songs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_llm_output_error_debug_includes_raw_response_path():
    """T35-Fix：LLMOutputError 时 error.details 应包含 raw_response_path / finish_reason / hint。"""
    from fastapi.exceptions import HTTPException
    from packages.llm.structured_call import LLMOutputError
    from services.api.routes.songs import _map_llm_exception

    exc = LLMOutputError("模型输出解析失败", task_name="generate_music_spec")
    exc.debug_info = {
        "provider": "gemini",
        "model": "gemini-3.5-flash",
        "finish_reason": "length",
        "content_chars": 2003,
        "raw_response_path": "data/llm_calls/xxx_raw_response.json",
        "message_content_path": "data/llm_calls/xxx_message_content.txt",
        "hint": "LLM output was truncated. Increase GEMINI_MAX_TOKENS.",
    }
    err = _map_llm_exception(exc, provider="gemini")
    assert isinstance(err, HTTPException)
    body = err.detail
    assert body["error_code"] == "LLM_INVALID_RESPONSE"
    assert body["details"]["finish_reason"] == "length"
    assert body["details"]["raw_response_path"] == "data/llm_calls/xxx_raw_response.json"
    assert body["details"]["message_content_path"] == "data/llm_calls/xxx_message_content.txt"
    assert "truncated" in body["details"]["hint"]
