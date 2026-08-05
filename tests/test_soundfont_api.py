"""T29：SoundFont API 测试。"""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def _create_song() -> str:
    resp = client.post("/api/v1/songs/generate", json={"prompt": "音源 API 测试"})
    assert resp.status_code == 200
    return resp.json()["song_id"]


def test_list_soundfonts_empty_no_crash():
    resp = client.get("/api/v1/soundfonts")
    assert resp.status_code == 200
    data = resp.json()
    assert "soundfonts" in data
    assert "default_soundfont_id" in data


def test_scan_soundfonts_ok():
    resp = client.post("/api/v1/soundfonts/scan")
    assert resp.status_code == 200
    assert "soundfonts" in resp.json()


def test_project_soundfont_put_missing_id_returns_warning():
    song_id = _create_song()
    resp = client.put(
        f"/api/v1/songs/{song_id}/soundfont",
        json={"soundfont_id": "missing-id"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is False
    assert data["warning"]
    assert data["soundfont"]["soundfont_id"] == "missing-id"


def test_project_soundfont_get_after_put(tmp_path, monkeypatch):
    # 准备一个本地音源
    monkeypatch.setenv("SOUNDFONT_DIR", str(tmp_path))
    (tmp_path / "Demo.sf2").write_bytes(b"fake-sf2")
    fonts = client.get("/api/v1/soundfonts").json()["soundfonts"]
    assert fonts
    soundfont_id = fonts[0]["id"]

    song_id = _create_song()
    resp = client.put(f"/api/v1/songs/{song_id}/soundfont", json={"soundfont_id": soundfont_id})
    assert resp.status_code == 200
    assert resp.json()["available"] is True
    assert resp.json()["warning"] is None

    got = client.get(f"/api/v1/songs/{song_id}/soundfont").json()
    assert got["soundfont"]["soundfont_id"] == soundfont_id
    assert got["available"] is True


def test_project_soundfont_missing_song_404():
    resp = client.get("/api/v1/songs/00000000-0000-0000-0000-000000000000/soundfont")
    assert resp.status_code == 404
