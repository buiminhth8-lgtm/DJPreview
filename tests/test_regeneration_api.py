"""局部重生成 API 测试。"""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def _create_song() -> str:
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    return resp.json()["song_id"]


def test_regenerate_section_creates_version():
    song_id = _create_song()
    before = client.get(f"/api/v1/songs/{song_id}/versions").json()["versions"]
    resp = client.post(
        f"/api/v1/songs/{song_id}/regenerate",
        json={
            "scope": "section",
            "section_id": "chorus",
            "instruction": "让副歌旋律变化更明显",
            "keep_harmony": True,
            "variation_strength": 0.7,
            "auto_render": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version_id"]
    assert data["parent_version_id"] == before[-1]["version_id"]
    chorus = next(s for s in data["music_spec"]["form"] if s["id"] == "chorus")
    verse = next(s for s in data["music_spec"]["form"] if s["id"] == "verse")
    assert verse["energy"] == 0.5  # 非目标段落不变
    assert chorus["energy"] != 0.9
    assert data["assets"]["has_midi"] is True


def test_regenerate_track_only_changes_track():
    song_id = _create_song()
    resp = client.post(
        f"/api/v1/songs/{song_id}/regenerate",
        json={"scope": "track", "track_id": "bass", "variation_strength": 0.8},
    )
    assert resp.status_code == 200
    bass = next(t for t in resp.json()["music_spec"]["tracks"] if t["id"] == "bass")
    assert bass["velocity"] != 90


def test_regenerate_missing_song_404():
    resp = client.post(
        "/api/v1/songs/00000000-0000-0000-0000-000000000000/regenerate",
        json={"scope": "overall"},
    )
    assert resp.status_code == 404
