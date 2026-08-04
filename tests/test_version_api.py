"""T05：版本详情 API 测试（GET /songs/{song_id}/versions/{version_id}）。"""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def _create_song() -> str:
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    assert resp.status_code == 200
    return resp.json()["song_id"]


def _versions(song_id: str) -> list[dict]:
    resp = client.get(f"/api/v1/songs/{song_id}/versions")
    assert resp.status_code == 200
    return resp.json()["versions"]


def test_get_v1_version_detail():
    song_id = _create_song()
    v1 = _versions(song_id)[0]
    resp = client.get(f"/api/v1/songs/{song_id}/versions/{v1['version_id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["song_id"] == song_id
    assert data["version_id"] == v1["version_id"]
    assert data["is_current"] is True
    assert data["metadata"]["index"] == 1
    assert data["metadata"]["parent_version_id"] is None
    assert data["music_spec"]["tempo"]["bpm"] == 72
    assert data["edit_spec"] is None
    assert data["diff"] is None
    assert data["assets"]["has_midi"] is False
    assert data["assets"]["has_audio"] is False


def test_get_v2_version_detail_after_edit():
    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "副歌更亮一点"})
    versions = _versions(song_id)
    v2 = versions[-1]
    assert v2["version_number"] == 2

    resp = client.get(f"/api/v1/songs/{song_id}/versions/{v2['version_id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_current"] is True
    assert data["metadata"]["index"] == 2
    assert data["metadata"]["edit_instruction"] == "副歌更亮一点"
    assert data["edit_spec"]["instruction"] == "副歌更亮一点"
    assert any(d["field"] == "form.chorus.energy" for d in data["diff"])
    assert data["assets"]["has_midi"] is True  # edit 会重渲染 MIDI/WAV
    assert data["assets"]["has_audio"] is True
    assert data["assets"]["midi_download_url"] == f"/api/v1/songs/{song_id}/midi/download"
    assert data["assets"]["audio_stream_url"] == f"/api/v1/songs/{song_id}/audio/stream"
    assert data["assets"]["audio_download_url"] == f"/api/v1/songs/{song_id}/audio/download"


def test_get_missing_version_404():
    song_id = _create_song()
    resp = client.get(f"/api/v1/songs/{song_id}/versions/not-exist")
    assert resp.status_code == 404
    assert "版本" in resp.json()["detail"]


def test_get_missing_song_404():
    resp = client.get("/api/v1/songs/00000000-0000-0000-0000-000000000000/versions/v1")
    assert resp.status_code == 404


# ---------- T06：版本 diff API ----------

def test_get_v1_version_diff():
    song_id = _create_song()
    v1 = _versions(song_id)[0]
    resp = client.get(f"/api/v1/songs/{song_id}/versions/{v1['version_id']}/diff")
    assert resp.status_code == 200
    data = resp.json()
    assert data["song_id"] == song_id
    assert data["version_id"] == v1["version_id"]
    assert data["parent_version_id"] is None
    assert data["is_current"] is True
    assert data["diff"] is None
    assert data["metadata"]["index"] == 1
    assert data["warnings"] == []


def test_get_v2_version_diff_after_edit():
    song_id = _create_song()
    versions = _versions(song_id)
    v1 = versions[0]
    client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "副歌更亮一点"})
    versions = _versions(song_id)
    v2 = versions[-1]

    resp = client.get(f"/api/v1/songs/{song_id}/versions/{v2['version_id']}/diff")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version_id"] == v2["version_id"]
    assert data["parent_version_id"] == v1["version_id"]
    assert data["is_current"] is True
    assert any(d["field"] == "form.chorus.energy" for d in data["diff"])
    assert data["metadata"]["edit_instruction"] == "副歌更亮一点"
    assert data["warnings"] == []


def test_get_missing_version_diff_404():
    song_id = _create_song()
    resp = client.get(f"/api/v1/songs/{song_id}/versions/not-exist/diff")
    assert resp.status_code == 404
    assert "版本" in resp.json()["detail"]


def test_get_missing_song_diff_404():
    resp = client.get("/api/v1/songs/00000000-0000-0000-0000-000000000000/versions/v1/diff")
    assert resp.status_code == 404


def test_diff_consistent_with_version_detail():
    """T05 版本详情接口的 diff 与 T06 diff 接口必须一致。"""
    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "整首更快一点"})
    versions = _versions(song_id)
    v2 = versions[-1]

    detail = client.get(f"/api/v1/songs/{song_id}/versions/{v2['version_id']}").json()
    diff_resp = client.get(f"/api/v1/songs/{song_id}/versions/{v2['version_id']}/diff").json()
    assert detail["diff"] == diff_resp["diff"]
