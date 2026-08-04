"""MIDI 生成 / 下载 API 集成测试。"""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def _create_song(prompt: str = "生成一段忧郁空灵的钢琴配乐") -> str:
    resp = client.post("/api/v1/songs/generate", json={"prompt": prompt})
    assert resp.status_code == 200
    return resp.json()["song_id"]


def test_generate_midi_endpoint():
    song_id = _create_song()
    resp = client.post(f"/api/v1/songs/{song_id}/midi/generate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["song_id"] == song_id
    assert data["midi_file"] == "output.mid"
    assert data["download_url"] == f"/api/v1/songs/{song_id}/midi/download"
    assert data["summary"]["bars"] == 32
    assert data["summary"]["bpm"] == 72
    assert data["summary"]["tracks"] >= 4


def test_download_midi_endpoint():
    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/midi/generate")
    resp = client.get(f"/api/v1/songs/{song_id}/midi/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("audio/midi")
    assert resp.content[:4] == b"MThd"
    assert resp.content != b""


def test_midi_generate_missing_song_404():
    resp = client.post("/api/v1/songs/00000000-0000-0000-0000-000000000000/midi/generate")
    assert resp.status_code == 404


def test_midi_download_before_generate_404():
    song_id = _create_song()
    resp = client.get(f"/api/v1/songs/{song_id}/midi/download")
    assert resp.status_code == 404


def test_generate_with_midi_endpoint():
    resp = client.post("/api/v1/songs/generate-with-midi", json={"prompt": "欢快明亮的流行歌"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["song_id"]
    assert data["music_spec"]["tempo"]["bpm"] == 120
    assert data["midi"]["midi_file"] == "output.mid"
    assert data["midi"]["download_url"].endswith("/midi/download")
