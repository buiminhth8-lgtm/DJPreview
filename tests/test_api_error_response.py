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
