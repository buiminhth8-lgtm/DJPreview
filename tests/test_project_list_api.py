"""T33.2：工程列表 / 删除 API 测试（unblocker：前端 /projects 页面需要）。"""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def _create_song(prompt: str = "生成一段忧郁空灵的钢琴配乐") -> str:
    resp = client.post("/api/v1/songs/generate", json={"prompt": prompt})
    assert resp.status_code == 200
    return resp.json()["song_id"]


def test_list_projects_contains_new_song():
    sid = _create_song()
    resp = client.get("/api/v1/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    ids = [p["song_id"] for p in data["projects"]]
    assert sid in ids
    item = next(p for p in data["projects"] if p["song_id"] == sid)
    assert item["title"]
    assert item["has_midi"] is False
    assert item["has_audio"] is False
    assert "current_version_id" in item


def test_list_projects_sorted_newest_first():
    sid_a = _create_song("列表排序测试 A")
    sid_b = _create_song("列表排序测试 B")
    resp = client.get("/api/v1/projects")
    ids = [p["song_id"] for p in resp.json()["projects"]]
    assert ids.index(sid_b) < ids.index(sid_a)


def test_delete_project():
    sid = _create_song("待删除工程")
    resp = client.delete(f"/api/v1/songs/{sid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["deleted"] is True
    # 删除后列表不再包含
    ids = [p["song_id"] for p in client.get("/api/v1/projects").json()["projects"]]
    assert sid not in ids


def test_delete_missing_project_404():
    missing = "00000000-0000-0000-0000-000000000000"
    resp = client.delete(f"/api/v1/songs/{missing}")
    assert resp.status_code == 404


def test_delete_invalid_id_400():
    resp = client.delete("/api/v1/songs/not-a-uuid")
    assert resp.status_code == 400
