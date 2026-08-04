"""T05：版本详情 API 测试（GET /songs/{song_id}/versions/{version_id}）。"""

import json

from fastapi.testclient import TestClient

from services.api.dependencies.config import get_settings
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
    assert "版本" in resp.json()["message"]


def test_get_missing_song_404():
    resp = client.get("/api/v1/songs/00000000-0000-0000-0000-000000000000/versions/v1")
    assert resp.status_code == 404


def test_new_project_uses_directory_layout_and_vn_ids():
    """T12：新项目 v1 使用目录式结构，version_id 为 v1。"""
    song_id = _create_song()
    data = client.get(f"/api/v1/songs/{song_id}/versions").json()
    v1 = data["versions"][0]
    assert v1["version_id"] == "v1"
    assert data["current_version_id"] == "v1"

    detail = client.get(f"/api/v1/songs/{song_id}/versions/v1").json()
    assert detail["version_id"] == "v1"
    assert detail["metadata"]["index"] == 1
    diff = client.get(f"/api/v1/songs/{song_id}/versions/v1/diff").json()
    assert diff["diff"] is None

    project_dir = get_settings().projects_dir / song_id
    assert (project_dir / "versions" / "v1" / "version_metadata.json").exists()
    assert (project_dir / "versions" / "v1" / "music_spec.json").exists()
    assert (project_dir / "current_version_id.txt").read_text(encoding="utf-8") == "v1"


def test_edit_creates_v2_directory_and_api_reads_it():
    """T12：编辑后 v2 目录包含 metadata / music_spec / edit_spec / diff。"""
    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "整首更快一点"})
    project_dir = get_settings().projects_dir / song_id
    v2 = project_dir / "versions" / "v2"
    assert (v2 / "version_metadata.json").exists()
    assert (v2 / "music_spec.json").exists()
    assert (v2 / "edit_spec.json").exists()
    assert (v2 / "diff.json").exists()
    assert (project_dir / "current_version_id.txt").read_text(encoding="utf-8") == "v2"

    detail = client.get(f"/api/v1/songs/{song_id}/versions/v2").json()
    assert detail["version_id"] == "v2"
    assert detail["is_current"] is True
    assert detail["edit_spec"]["instruction"] == "整首更快一点"
    assert any(d["field"] == "tempo.bpm" for d in detail["diff"])

    diff = client.get(f"/api/v1/songs/{song_id}/versions/v2/diff").json()
    assert diff["parent_version_id"] == "v1"
    assert any(d["field"] == "tempo.bpm" for d in diff["diff"])


# ---------- T13：恢复版本完整资产 ----------

def test_restore_updates_current_version_pointer():
    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "整首更快一点"})
    resp = client.post(f"/api/v1/songs/{song_id}/versions/v1/restore")
    assert resp.status_code == 200
    data = resp.json()
    assert data["restored_version_id"] == "v1"
    assert data["current_version_id"] == "v1"

    project_dir = get_settings().projects_dir / song_id
    assert (project_dir / "current_version_id.txt").read_text(encoding="utf-8") == "v1"
    index = json.loads((project_dir / "versions" / "index.json").read_text(encoding="utf-8"))
    assert index["current_version_id"] == "v1"
    versions = client.get(f"/api/v1/songs/{song_id}/versions").json()
    assert versions["current_version_id"] == "v1"


def test_restore_recovers_music_spec():
    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "整首更快一点"})
    resp = client.post(f"/api/v1/songs/{song_id}/versions/v1/restore")
    assert resp.status_code == 200
    assert resp.json()["music_spec"]["tempo"]["bpm"] == 72

    project_dir = get_settings().projects_dir / song_id
    root_spec = json.loads((project_dir / "music_spec.json").read_text(encoding="utf-8"))
    v1_spec = json.loads((project_dir / "versions" / "v1" / "music_spec.json").read_text(encoding="utf-8"))
    assert root_spec == v1_spec
    assert root_spec["tempo"]["bpm"] == 72
    got = client.get(f"/api/v1/songs/{song_id}").json()
    assert got["music_spec"]["tempo"]["bpm"] == 72


def test_restore_does_not_regenerate_midi_or_wav(monkeypatch):
    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "整首更快一点"})

    def boom(*args, **kwargs):
        raise AssertionError("restore 不应重新生成 MIDI / WAV")

    monkeypatch.setattr("services.api.routes.songs._generate_midi_for", boom)
    monkeypatch.setattr("services.api.routes.songs._render_audio_for", boom)
    resp = client.post(f"/api/v1/songs/{song_id}/versions/v1/restore")
    assert resp.status_code == 200
    assert resp.json()["restored_version_id"] == "v1"


def test_restore_copies_midi_asset():
    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/midi/generate")
    project_dir = get_settings().projects_dir / song_id
    v1_midi = (project_dir / "versions" / "v1" / "output.mid").read_bytes()
    assert v1_midi

    client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "整首更快一点"})
    resp = client.post(f"/api/v1/songs/{song_id}/versions/v1/restore")
    assert resp.status_code == 200
    assert (project_dir / "output.mid").read_bytes() == v1_midi
    assert (project_dir / "versions" / "v1" / "output.mid").read_bytes() == v1_midi


def test_restore_to_no_audio_version_cleans_wav():
    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "整首更快一点"})
    project_dir = get_settings().projects_dir / song_id
    assert (project_dir / "output.wav").exists()  # v2 渲染过音频

    resp = client.post(f"/api/v1/songs/{song_id}/versions/v1/restore")
    assert resp.status_code == 200
    assert not (project_dir / "output.wav").exists()
    assert not (project_dir / "audio_metadata.json").exists()

    assets = client.get(f"/api/v1/songs/{song_id}/assets").json()
    assert assets["has_audio"] is False
    download = client.get(f"/api/v1/songs/{song_id}/audio/download")
    assert download.status_code == 404
    assert download.json()["error_code"] == "ASSET_NOT_FOUND"


def test_restore_recovers_mix_and_cleans_quality():
    song_id = _create_song()
    project_dir = get_settings().projects_dir / song_id
    client.get(f"/api/v1/songs/{song_id}/mix")  # 创建 v1 mix
    v1_mix = json.loads((project_dir / "versions" / "v1" / "mix_spec.json").read_text(encoding="utf-8"))

    client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "整首更快一点"})
    v2_mix = {**v1_mix, "notes": "v2 changed"}
    (project_dir / "versions" / "v2" / "mix_spec.json").write_text(
        json.dumps(v2_mix, ensure_ascii=False), encoding="utf-8"
    )
    (project_dir / "mix_spec.json").write_text(
        json.dumps(v2_mix, ensure_ascii=False), encoding="utf-8"
    )
    client.post(f"/api/v1/songs/{song_id}/quality/check")  # v2 生成 quality
    assert (project_dir / "quality_report.json").exists()

    resp = client.post(f"/api/v1/songs/{song_id}/versions/v1/restore")
    assert resp.status_code == 200
    data = resp.json()
    assert json.loads((project_dir / "mix_spec.json").read_text(encoding="utf-8")) == v1_mix
    assert not (project_dir / "quality_report.json").exists()
    assert "mix_spec.json" in data["restore_summary"]["restored"]
    assert "quality_report.json" in data["restore_summary"]["removed"]


def test_restore_missing_version_404():
    song_id = _create_song()
    resp = client.post(f"/api/v1/songs/{song_id}/versions/not-exist/restore")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "VERSION_NOT_FOUND"


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
    assert "版本" in resp.json()["message"]


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
