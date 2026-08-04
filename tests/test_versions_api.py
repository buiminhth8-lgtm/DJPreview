"""第四阶段：版本管理 API 测试。"""

import json

from fastapi.testclient import TestClient

from services.api.dependencies.config import get_settings
from services.api.main import app

client = TestClient(app)


def _create_song(prompt: str = "生成一段忧郁空灵的钢琴配乐") -> str:
    resp = client.post("/api/v1/songs/generate", json={"prompt": prompt})
    assert resp.status_code == 200
    return resp.json()["song_id"]


def _root_spec(song_id: str) -> dict:
    path = get_settings().projects_dir / song_id / "music_spec.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_old_project_auto_init_v1():
    song_id = _create_song()
    resp = client.get(f"/api/v1/songs/{song_id}/versions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["versions"]) == 1
    assert data["versions"][0]["version_number"] == 1
    assert data["current_version_id"] == data["versions"][0]["version_id"]


def test_edit_creates_new_version():
    song_id = _create_song()
    resp = client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "整首更快一点"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["version_id"]
    assert data["edit_spec"]["instruction"] == "整首更快一点"
    assert any(d["field"] == "tempo.bpm" for d in data["diff"])
    assert data["assets"]["current_version"]["version_number"] == 2
    assert data["music_spec"]["tempo"]["bpm"] == 82

    versions = client.get(f"/api/v1/songs/{song_id}/versions").json()
    assert len(versions["versions"]) == 2
    assert versions["current_version_id"] == data["version_id"]
    # 根目录 music_spec.json 已同步
    assert _root_spec(song_id)["tempo"]["bpm"] == 82


def test_restore_returns_v1_and_syncs_root():
    song_id = _create_song()
    first = client.get(f"/api/v1/songs/{song_id}/versions").json()["versions"][0]
    client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "整首更快一点"})

    resp = client.post(f"/api/v1/songs/{song_id}/versions/{first['version_id']}/restore")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version_id"] == first["version_id"]
    assert data["music_spec"]["tempo"]["bpm"] == 72
    assert data["assets"]["current_version"]["version_number"] == 1
    # 根目录 music_spec.json 同步为 v1
    assert _root_spec(song_id)["tempo"]["bpm"] == 72


def test_assets_has_current_version():
    song_id = _create_song()
    assets = client.get(f"/api/v1/songs/{song_id}/assets").json()
    assert assets["current_version"]["version_number"] == 1
    client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "加点中国风"})
    assets = client.get(f"/api/v1/songs/{song_id}/assets").json()
    assert assets["current_version"]["version_number"] == 2


def test_section_edit_via_api():
    song_id = _create_song()
    resp = client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "副歌更亮一点"})
    assert resp.status_code == 200
    new = resp.json()["music_spec"]
    chorus = next(s for s in new["form"] if s["id"] == "chorus")
    assert chorus["energy"] > 0.9
    verse = next(s for s in new["form"] if s["id"] == "verse")
    assert verse["energy"] == 0.5  # 其他段落不变


def test_edit_regenerates_midi_and_audio():
    song_id = _create_song()
    resp = client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "整首更快一点"})
    assert resp.status_code == 200
    assets = resp.json()["assets"]
    assert assets["has_midi"] is True
    assert assets["has_audio"] is True


def test_edit_missing_song_404():
    resp = client.post(
        "/api/v1/songs/00000000-0000-0000-0000-000000000000/edit",
        json={"instruction": "更快"},
    )
    assert resp.status_code == 404


def test_restore_missing_version_404():
    song_id = _create_song()
    resp = client.post(
        f"/api/v1/songs/{song_id}/versions/00000000-0000-0000-0000-000000000000/restore"
    )
    assert resp.status_code == 404


def test_edit_empty_instruction_422():
    song_id = _create_song()
    resp = client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "   "})
    assert resp.status_code == 422
