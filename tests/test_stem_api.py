"""Stems 导出 API 测试。"""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def _create_song() -> str:
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    return resp.json()["song_id"]


def test_stems_export_and_downloads():
    song_id = _create_song()
    resp = client.post(f"/api/v1/songs/{song_id}/stems/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stems"]
    assert data["zip_download_url"].endswith("/stems/download")

    first = data["stems"][0]
    midi_resp = client.get(first["midi_download_url"])
    assert midi_resp.status_code == 200
    assert midi_resp.content[:4] == b"MThd"

    wav_resp = client.get(first["wav_download_url"])
    assert wav_resp.status_code == 200
    assert wav_resp.content[:4] == b"RIFF"

    zip_resp = client.get(data["zip_download_url"])
    assert zip_resp.status_code == 200
    assert zip_resp.content[:2] == b"PK"
    assert len(zip_resp.content) > 0


def test_stem_missing_track_404():
    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/stems/export")
    resp = client.get(f"/api/v1/songs/{song_id}/stems/not_a_track/midi/download")
    assert resp.status_code == 404


def test_stem_invalid_kind_400():
    song_id = _create_song()
    resp = client.get(f"/api/v1/songs/{song_id}/stems/melody/mp3/download")
    assert resp.status_code == 400


def test_stems_missing_song_404():
    resp = client.post("/api/v1/songs/00000000-0000-0000-0000-000000000000/stems/export")
    assert resp.status_code == 404
