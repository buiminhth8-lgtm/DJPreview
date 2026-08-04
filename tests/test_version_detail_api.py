"""版本详情与 diff API 测试。"""

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


def test_version_detail():
    song_id = _create_song()
    v1 = _versions(song_id)[0]
    resp = client.get(f"/api/v1/songs/{song_id}/versions/{v1['version_id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version_id"] == v1["version_id"]
    assert data["version_number"] == 1
    assert data["music_spec"]["tempo"]["bpm"] == 72
    assert data["edit_spec"] is None
    assert data["is_current"] is True
    assert data["assets"]["song_id"] == song_id


def test_version_detail_after_edit_has_edit_spec_and_not_current():
    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "整首更快一点"})
    versions = _versions(song_id)
    v1 = versions[0]
    v2 = versions[-1]

    resp1 = client.get(f"/api/v1/songs/{song_id}/versions/{v1['version_id']}")
    assert resp1.json()["is_current"] is False
    assert resp1.json()["music_spec"]["tempo"]["bpm"] == 72

    resp2 = client.get(f"/api/v1/songs/{song_id}/versions/{v2['version_id']}")
    data2 = resp2.json()
    assert data2["is_current"] is True
    assert data2["edit_spec"]["instruction"] == "整首更快一点"
    assert data2["music_spec"]["tempo"]["bpm"] == 82


def test_version_diff_after_edit():
    song_id = _create_song()
    v1 = _versions(song_id)[0]
    client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "整首更快一点"})

    resp = client.get(f"/api/v1/songs/{song_id}/versions/{v1['version_id']}/diff")
    assert resp.status_code == 200
    data = resp.json()
    fields = {d["field"] for d in data["diff"]}
    assert "tempo.bpm" in fields
    tempo = next(d for d in data["diff"] if d["field"] == "tempo.bpm")
    assert tempo["old"] == 72
    assert tempo["new"] == 82
    assert data["base_version_number"] == 2
    assert data["is_current"] is False
    assert data["music_spec"]["tempo"]["bpm"] == 72  # 返回目标版本 spec
    assert data["assets"]["song_id"] == song_id


def test_version_diff_current_version_empty():
    song_id = _create_song()
    v1 = _versions(song_id)[0]
    resp = client.get(f"/api/v1/songs/{song_id}/versions/{v1['version_id']}/diff")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_current"] is True
    assert data["diff"] == []


def test_version_detail_missing_version_404():
    song_id = _create_song()
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/api/v1/songs/{song_id}/versions/{missing}").status_code == 404
    assert client.get(f"/api/v1/songs/{song_id}/versions/{missing}/diff").status_code == 404


def test_version_detail_missing_song_404():
    missing_song = "00000000-0000-0000-0000-000000000000"
    version = "00000000-0000-0000-0000-000000000001"
    assert client.get(f"/api/v1/songs/{missing_song}/versions/{version}").status_code == 404
    assert client.get(f"/api/v1/songs/{missing_song}/versions/{version}/diff").status_code == 404
