"""混音 API 测试。"""

from fastapi.testclient import TestClient

from services.api.dependencies.config import get_settings
from services.api.main import app

client = TestClient(app)


def _create_song() -> str:
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    assert resp.status_code == 200
    return resp.json()["song_id"]


def test_get_mix_returns_default():
    song_id = _create_song()
    resp = client.get(f"/api/v1/songs/{song_id}/mix")
    assert resp.status_code == 200
    data = resp.json()
    assert data["song_id"] == song_id
    assert len(data["mix_spec"]["tracks"]) == 5


def test_patch_mix_updates_volume_and_saves():
    song_id = _create_song()
    resp = client.patch(
        f"/api/v1/songs/{song_id}/mix",
        json={"tracks": [{"track_id": "piano", "volume": 0.7, "pan": -0.2}]},
    )
    assert resp.status_code == 200
    mix = resp.json()["mix_spec"]
    piano = next(t for t in mix["tracks"] if t["track_id"] == "piano")
    assert piano["volume"] == 0.7
    assert piano["pan"] == -0.2
    # mix_spec.json 已保存
    saved = get_settings().projects_dir / song_id / "mix_spec.json"
    assert saved.exists()


def test_patch_mix_with_apply_regenerates():
    song_id = _create_song()
    resp = client.patch(
        f"/api/v1/songs/{song_id}/mix?apply=true",
        json={"tracks": [{"track_id": "bass", "volume": 0.6}]},
    )
    assert resp.status_code == 200
    assets = resp.json()["assets"]
    assert assets["has_midi"] is True
    assert assets["has_audio"] is True


def test_apply_mix_endpoint():
    song_id = _create_song()
    client.patch(
        f"/api/v1/songs/{song_id}/mix",
        json={"tracks": [{"track_id": "piano", "solo": True}]},
    )
    resp = client.post(f"/api/v1/songs/{song_id}/mix/apply")
    assert resp.status_code == 200
    data = resp.json()
    assert data["assets"]["has_midi"] is True
    assert data["assets"]["has_audio"] is True
    assert isinstance(data["warnings"], list)


def test_mix_missing_song_404():
    assert client.get("/api/v1/songs/00000000-0000-0000-0000-000000000000/mix").status_code == 404
