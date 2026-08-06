"""T35：request_id 中间件测试。"""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def _generate() -> dict:
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    assert resp.status_code == 200, resp.text
    return resp


def test_success_response_contains_request_id():
    resp = _generate()
    body = resp.json()
    assert body["request_id"]
    assert resp.headers.get("X-Request-ID") == body["request_id"]


def test_error_response_contains_request_id():
    resp = client.get("/api/v1/songs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    body = resp.json()
    assert body["request_id"]
    assert body["success"] is False
    assert resp.headers.get("X-Request-ID") == body["request_id"]


def test_response_header_x_request_id_present():
    resp = _generate()
    assert resp.headers.get("X-Request-ID")


def test_reuses_incoming_x_request_id():
    custom = "my-custom-request-123"
    resp = client.post(
        "/api/v1/songs/generate",
        json={"prompt": "欢快明亮的流行歌"},
        headers={"X-Request-ID": custom},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["request_id"] == custom
    assert resp.headers.get("X-Request-ID") == custom


def test_health_includes_request_id():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["request_id"]
    assert resp.headers.get("X-Request-ID")
