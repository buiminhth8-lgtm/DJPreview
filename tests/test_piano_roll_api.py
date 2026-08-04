"""Piano Roll API 测试。"""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def _create_song() -> str:
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    return resp.json()["song_id"]


def test_piano_roll_auto_generates_midi():
    song_id = _create_song()
    resp = client.get(f"/api/v1/songs/{song_id}/piano-roll")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tracks"]
    assert any(t["notes"] for t in data["tracks"])
    assert data["beats_per_bar"] == 4
    assert data["sections"]


def test_piano_roll_track_filter():
    song_id = _create_song()
    resp = client.get(f"/api/v1/songs/{song_id}/piano-roll?track_id=melody")
    assert resp.status_code == 200
    data = resp.json()
    assert all(t["role"] == "melody" for t in data["tracks"])


def test_piano_roll_missing_song_404():
    resp = client.get("/api/v1/songs/00000000-0000-0000-0000-000000000000/piano-roll")
    assert resp.status_code == 404
