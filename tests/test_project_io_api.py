"""工程导入导出 API 测试。"""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def test_export_and_import_project():
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    song_id = resp.json()["song_id"]
    client.post(f"/api/v1/songs/{song_id}/midi/generate")

    export = client.get(f"/api/v1/songs/{song_id}/project/export")
    assert export.status_code == 200
    assert export.content[:2] == b"PK"

    import_resp = client.post(
        "/api/v1/projects/import",
        files={"file": ("project.aimusic.zip", export.content, "application/zip")},
    )
    assert import_resp.status_code == 200
    data = import_resp.json()
    assert data["imported"] is True
    assert data["song_id"] != song_id
    assert data["summary"]["has_midi"] is True
    assert data["source_song_id"] == song_id
    assert data["current_version_id"] == "v1"
    assert data["version_count"] == 1
    assert data["assets"]["has_midi"] is True
    assert data["assets"]["has_audio"] is False
    assert isinstance(data["warnings"], list)

    # 导入后的版本 API 可用
    imported_song_id = data["song_id"]
    versions = client.get(f"/api/v1/songs/{imported_song_id}/versions")
    assert versions.status_code == 200
    assert len(versions.json()["versions"]) == 1
    assert versions.json()["current_version_id"] == "v1"

    detail = client.get(f"/api/v1/songs/{imported_song_id}/versions/v1")
    assert detail.status_code == 200
    assert detail.json()["music_spec"]["tempo"]["bpm"] == 72

    diff = client.get(f"/api/v1/songs/{imported_song_id}/versions/v1/diff")
    assert diff.status_code == 200
    assert diff.json()["diff"] is None

    restore = client.post(f"/api/v1/songs/{imported_song_id}/versions/v1/restore")
    assert restore.status_code == 200
    assert restore.json()["version_id"] == "v1"


def test_import_invalid_zip_400():
    resp = client.post(
        "/api/v1/projects/import",
        files={"file": ("bad.zip", b"not a zip", "application/zip")},
    )
    assert resp.status_code == 400


def test_evaluation_cases_and_run():
    cases = client.get("/api/v1/evaluation/cases")
    assert cases.status_code == 200
    assert len(cases.json()) >= 8

    ids = [c["id"] for c in cases.json()[:2]]
    report = client.post("/api/v1/evaluation/run", json={"case_ids": ids, "render_audio": False})
    assert report.status_code == 200
    data = report.json()
    assert data["total_cases"] == 2
    assert 0 <= data["average_score"] <= 100
