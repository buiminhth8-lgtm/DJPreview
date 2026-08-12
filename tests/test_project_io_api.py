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


def test_export_import_preserves_manual_midi_edit_version():
    """T34.10：Manual MIDI Edit 版本经 bundle roundtrip 后仍是 current 且 Editor 可读。"""
    resp = client.post("/api/v1/songs/generate", json={"prompt": "带 Bass 与 Drums 的最终验收配乐"})
    song_id = resp.json()["song_id"]
    assert client.post(f"/api/v1/songs/{song_id}/midi/generate").status_code == 200

    before = client.get(f"/api/v1/songs/{song_id}/midi/editor").json()
    bass = next(track for track in before["tracks"] if track["role"] == "bass")
    edited_notes = [
        {
            **bass["notes"][0],
            "pitch": max(0, bass["notes"][0]["pitch"] - 1),
            "velocity": 77,
        }
    ]
    save = client.post(
        f"/api/v1/songs/{song_id}/midi/edit",
        json={"track_id": bass["id"], "base_version_id": before["version_id"], "notes": edited_notes},
    )
    assert save.status_code == 200
    manual_version_id = save.json()["version_id"]

    export = client.get(f"/api/v1/songs/{song_id}/project/export")
    assert export.status_code == 200
    imported = client.post(
        "/api/v1/projects/import",
        files={"file": ("manual.aimusic.zip", export.content, "application/zip")},
    )
    assert imported.status_code == 200
    imported_data = imported.json()
    assert imported_data["current_version_id"] == manual_version_id
    assert imported_data["version_count"] == 2
    assert imported_data["assets"]["has_midi"] is True

    imported_id = imported_data["song_id"]
    imported_doc = client.get(f"/api/v1/songs/{imported_id}/midi/editor")
    assert imported_doc.status_code == 200
    imported_body = imported_doc.json()
    assert imported_body["version_id"] == manual_version_id
    imported_bass = next(track for track in imported_body["tracks"] if track["id"] == bass["id"])
    assert len(imported_bass["notes"]) == 1
    assert imported_bass["notes"][0]["pitch"] == edited_notes[0]["pitch"]
    assert imported_bass["notes"][0]["velocity"] == 77
    assert imported_bass["notes"][0]["channel"] == bass["channel"]
    assert client.get(f"/api/v1/songs/{imported_id}").json()["music_spec"] == resp.json()["music_spec"]


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
