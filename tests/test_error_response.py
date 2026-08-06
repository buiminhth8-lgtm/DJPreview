"""T08：统一 API 错误响应测试。"""

import zipfile
import asyncio
import json

from fastapi import HTTPException
from fastapi.testclient import TestClient

from services.api.main import app, http_exception_handler

client = TestClient(app)


def _create_song() -> str:
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    assert resp.status_code == 200
    return resp.json()["song_id"]


def _assert_error(body: dict, error_code: str):
    assert body["error_code"] == error_code
    assert isinstance(body["message"], str) and body["message"]
    assert isinstance(body["details"], dict)


def test_project_not_found():
    resp = client.get("/api/v1/songs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    body = resp.json()
    _assert_error(body, "PROJECT_NOT_FOUND")
    assert body["details"].get("song_id") == "00000000-0000-0000-0000-000000000000"


def test_version_not_found():
    song_id = _create_song()
    resp = client.get(f"/api/v1/songs/{song_id}/versions/not-exist")
    assert resp.status_code == 404
    body = resp.json()
    _assert_error(body, "VERSION_NOT_FOUND")
    assert body["details"].get("version_id") == "not-exist"


def test_version_diff_not_found():
    song_id = _create_song()
    resp = client.get(f"/api/v1/songs/{song_id}/versions/not-exist/diff")
    assert resp.status_code == 404
    _assert_error(resp.json(), "VERSION_NOT_FOUND")


def test_asset_not_found():
    song_id = _create_song()
    resp = client.get(f"/api/v1/songs/{song_id}/audio/download")
    assert resp.status_code == 404
    body = resp.json()
    _assert_error(body, "ASSET_NOT_FOUND")
    assert body["details"].get("asset") == "output.wav"


def test_midi_asset_not_found():
    song_id = _create_song()
    resp = client.get(f"/api/v1/songs/{song_id}/midi/download")
    assert resp.status_code == 404
    _assert_error(resp.json(), "ASSET_NOT_FOUND")


def test_invalid_project_bundle(tmp_path):
    bad_zip = tmp_path / "bad.aimusic.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("some.txt", "not a manifest")
    with open(bad_zip, "rb") as f:
        resp = client.post("/api/v1/projects/import", files={"file": ("bad.aimusic.zip", f, "application/zip")})
    assert resp.status_code in (400, 422)
    _assert_error(resp.json(), "INVALID_PROJECT_BUNDLE")


def test_plain_http_exception_fallback():
    """字符串 detail 的普通 HTTPException 也应被转换为统一结构。"""

    async def _run():
        response = await http_exception_handler(None, HTTPException(status_code=400, detail="boom"))
        return json.loads(response.body), response.status_code

    body, status = asyncio.run(_run())
    assert status == 400
    assert body["success"] is False
    assert body["error_code"] == "HTTP_ERROR"
    assert body["message"] == "boom"
    assert body["details"] == {}
    assert body["error"]["code"] == "HTTP_ERROR"
    assert body["error"]["stage"] == "unknown"


def test_structured_detail_passthrough():
    """结构化 dict detail 展开为 T35 错误结构（保留旧字段 + 新增 error 对象）。"""
    detail = {
        "error_code": "PROJECT_NOT_FOUND",
        "message": "项目不存在",
        "details": {"song_id": "x"},
    }

    async def _run():
        response = await http_exception_handler(None, HTTPException(status_code=404, detail=detail))
        return json.loads(response.body)

    body = asyncio.run(_run())
    assert body["success"] is False
    assert body["error_code"] == "PROJECT_NOT_FOUND"
    assert body["message"] == "项目不存在"
    assert body["details"] == {"song_id": "x"}
    assert body["error"]["code"] == "PROJECT_NOT_FOUND"
    assert body["error"]["message"] == "项目不存在"
    assert body["error"]["details"] == {"song_id": "x"}


def test_invalid_eval_case_selection():
    """无效 case_id 列表返回结构化 INVALID_REQUEST。"""
    resp = client.post(
        "/api/v1/evaluation/run",
        json={"case_ids": ["no_such_case"], "render_audio": False},
    )
    assert resp.status_code == 400
    _assert_error(resp.json(), "INVALID_REQUEST")
