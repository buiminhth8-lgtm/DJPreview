"""风格模板 API 测试。"""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def test_list_styles():
    resp = client.get("/api/v1/styles")
    assert resp.status_code == 200
    assert len(resp.json()) >= 8


def test_get_style():
    resp = client.get("/api/v1/styles/cinematic_piano")
    assert resp.status_code == 200
    assert resp.json()["id"] == "cinematic_piano"


def test_get_style_missing_404():
    assert client.get("/api/v1/styles/nope").status_code == 404


def test_generate_with_style_template():
    resp = client.post(
        "/api/v1/songs/generate",
        json={
            "prompt": "生成一段雨夜电影钢琴配乐",
            "style_template_id": "cinematic_piano",
            "style_strength": 0.8,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["style_template"]["id"] == "cinematic_piano"
    assert "cinematic" in data["music_spec"]["style"]


def test_generate_without_style_keeps_compat():
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴曲"})
    assert resp.status_code == 200
    assert resp.json()["style_template"] is None
