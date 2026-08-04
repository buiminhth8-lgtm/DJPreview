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


def test_generated_harmony_parseable():
    """T19：MockProvider 生成的 harmony 全部可解析。"""
    from packages.music_core.theory.chords import is_valid_chord_symbol

    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["music_spec"]["harmony"]
    for section in data["music_spec"]["harmony"]:
        assert section["progression"]
        assert all(is_valid_chord_symbol(c) for c in section["progression"])


def test_generated_song_has_drums_track():
    """T20：MockProvider 默认生成包含 drums track。"""
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    assert resp.status_code == 200
    tracks = resp.json()["music_spec"]["tracks"]
    assert any(t["role"] == "drums" for t in tracks)


def test_generated_song_has_bass_track():
    """T21：MockProvider 默认生成包含 bass track。"""
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    assert resp.status_code == 200
    tracks = resp.json()["music_spec"]["tracks"]
    assert any(t["role"] == "bass" for t in tracks)


def test_cinematic_prompt_has_strings_and_pad():
    """T22：cinematic / chinese cinematic prompt 生成 strings 与 pad。"""
    resp = client.post("/api/v1/songs/generate", json={"prompt": "cinematic 电影配乐"})
    assert resp.status_code == 200
    roles = {t["role"] for t in resp.json()["music_spec"]["tracks"]}
    assert "strings" in roles
    assert "pad" in roles

    resp2 = client.post("/api/v1/songs/generate", json={"prompt": "带有中国风韵味的旋律"})
    assert resp2.status_code == 200
    roles2 = {t["role"] for t in resp2.json()["music_spec"]["tracks"]}
    assert "strings" in roles2
    assert "pad" in roles2
