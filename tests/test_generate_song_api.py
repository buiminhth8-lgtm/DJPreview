"""歌曲生成 / 查询 API 集成测试。"""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_generate_and_get_song():
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    assert resp.status_code == 200
    data = resp.json()
    assert "song_id" in data
    assert data["music_spec"]["version"] == "0.1"
    assert data["music_spec"]["tempo"]["bpm"] == 72
    assert data["music_spec"]["tonality"]["key"] == "D"
    assert len(data["music_spec"]["tracks"]) >= 5

    song_id = data["song_id"]
    resp2 = client.get(f"/api/v1/songs/{song_id}")
    assert resp2.status_code == 200
    got = resp2.json()
    assert got["song_id"] == song_id
    assert got["music_spec"]["prompt"] == "生成一段忧郁空灵的钢琴配乐"


def test_empty_prompt_rejected():
    resp = client.post("/api/v1/songs/generate", json={"prompt": "   "})
    assert resp.status_code == 422


def test_get_missing_song_returns_404():
    resp = client.get("/api/v1/songs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
