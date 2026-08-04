"""T12：目录式版本资产结构测试（项目存储层）。"""

import json

from packages.music_core.versioning.version_migration import ensure_version_layout
from services.api.storage import project_store
from services.api.storage.project_store import (
    create_project,
    create_version,
    save_audio_metadata,
    save_midi_file,
)
from tests.test_harmony_engine import build_spec


def _setup(tmp_path, monkeypatch):
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    settings = type("Settings", (), {"projects_dir": projects_dir})()
    monkeypatch.setattr(project_store, "get_settings", lambda: settings)
    return projects_dir


def _new_spec():
    return build_spec()


def _edit_spec_dict():
    return {
        "version": "0.1",
        "instruction": "更快",
        "target": {"scope": "overall", "section": None, "track": None},
        "preserve": ["version"],
        "operations": [{"type": "tempo", "amount": 10.0, "value": None, "params": {"bpm": 82}}],
    }


def test_new_project_directory_layout(tmp_path, monkeypatch):
    projects = _setup(tmp_path, monkeypatch)
    song_id = create_project(_new_spec())
    project_dir = projects / song_id

    assert (project_dir / "music_spec.json").exists()
    assert (project_dir / "current.json").exists()
    assert (project_dir / "current_version_id.txt").read_text(encoding="utf-8") == "v1"

    index = json.loads((project_dir / "versions" / "index.json").read_text(encoding="utf-8"))
    assert index["schema_version"] == 2
    assert index["current_version_id"] == "v1"
    assert len(index["versions"]) == 1
    assert index["versions"][0]["path"] == "versions/v1"

    v1 = project_dir / "versions" / "v1"
    assert (v1 / "version_metadata.json").exists()
    assert (v1 / "music_spec.json").exists()
    metadata = json.loads((v1 / "version_metadata.json").read_text(encoding="utf-8"))
    assert metadata["version_id"] == "v1"
    assert metadata["index"] == 1
    assert metadata["kind"] == "initial"


def test_edit_creates_v2_directory(tmp_path, monkeypatch):
    projects = _setup(tmp_path, monkeypatch)
    song_id = create_project(_new_spec())
    base = _new_spec()
    new_spec = base.model_copy(update={"tempo": base.tempo.model_copy(update={"bpm": 82})})
    version = create_version(song_id, new_spec, "更快", _edit_spec_dict())

    assert version["version_id"] == "v2"
    project_dir = projects / song_id
    v2 = project_dir / "versions" / "v2"
    assert (v2 / "version_metadata.json").exists()
    assert (v2 / "music_spec.json").exists()
    assert (v2 / "edit_spec.json").exists()
    assert (v2 / "diff.json").exists()
    assert (project_dir / "current_version_id.txt").read_text(encoding="utf-8") == "v2"

    index = json.loads((project_dir / "versions" / "index.json").read_text(encoding="utf-8"))
    assert index["current_version_id"] == "v2"
    assert len(index["versions"]) == 2

    diff = json.loads((v2 / "diff.json").read_text(encoding="utf-8"))
    assert any(d["field"] == "tempo.bpm" for d in diff)
    saved_edit = json.loads((v2 / "edit_spec.json").read_text(encoding="utf-8"))
    assert saved_edit["instruction"] == "更快"

    # 根目录兼容镜像同步
    root_spec = json.loads((project_dir / "music_spec.json").read_text(encoding="utf-8"))
    assert root_spec["tempo"]["bpm"] == 82


def test_midi_asset_synced_to_version_dir(tmp_path, monkeypatch):
    projects = _setup(tmp_path, monkeypatch)
    song_id = create_project(_new_spec())
    save_midi_file(song_id, b"MThd-test")
    project_dir = projects / song_id
    assert (project_dir / "output.mid").exists()
    assert (project_dir / "versions" / "v1" / "output.mid").exists()


def test_wav_and_metadata_synced_to_version_dir(tmp_path, monkeypatch):
    projects = _setup(tmp_path, monkeypatch)
    song_id = create_project(_new_spec())
    (projects / song_id / "output.wav").write_bytes(b"RIFF-test")
    save_audio_metadata(song_id, {"renderer": "fallback", "sample_rate": 44100, "duration_seconds": 1.0})
    project_dir = projects / song_id
    assert (project_dir / "output.wav").exists()
    assert (project_dir / "audio_metadata.json").exists()
    assert (project_dir / "versions" / "v1" / "output.wav").exists()
    assert (project_dir / "versions" / "v1" / "audio_metadata.json").exists()


def test_legacy_layout_migrated_idempotently(tmp_path):
    project = tmp_path / "legacy"
    (project / "versions").mkdir(parents=True)
    spec = _new_spec()
    (project / "music_spec.json").write_text(
        json.dumps(spec.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8"
    )
    old_id = "11111111-1111-1111-1111-111111111111"
    legacy_snapshot = {
        "version_id": old_id,
        "version_number": 1,
        "created_at": "2026-01-01T00:00:00Z",
        "instruction": None,
        "parent_version_id": None,
        "edit_spec": None,
        "music_spec": spec.model_dump(mode="json"),
    }
    (project / "versions" / "v1.json").write_text(
        json.dumps(legacy_snapshot, ensure_ascii=False), encoding="utf-8"
    )
    (project / "versions" / "index.json").write_text(
        json.dumps(
            {
                "current_version_id": old_id,
                "versions": [
                    {
                        "version_id": old_id,
                        "version_number": 1,
                        "created_at": "2026-01-01T00:00:00Z",
                        "instruction": None,
                        "parent_version_id": None,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    index = ensure_version_layout(project)
    assert index["schema_version"] == 2
    assert (project / "versions" / "v1" / "version_metadata.json").exists()
    assert (project / "versions" / "v1" / "music_spec.json").exists()
    assert (project / "versions" / "v1.json").exists()  # 旧文件保留为兼容备份
    assert (project / "current_version_id.txt").read_text(encoding="utf-8") == "v1"
    assert (project / "current.json").exists()

    # 可重复执行
    index2 = ensure_version_layout(project)
    assert index2["schema_version"] == 2
    assert index2["current_version_id"] == "v1"
    assert (project / "versions" / "v1" / "music_spec.json").exists()


def test_migration_falls_back_to_root_spec(tmp_path):
    """只有 index 没有 vN.json 的项目（如导入工程）也能迁移。"""
    project = tmp_path / "legacy2"
    (project / "versions").mkdir(parents=True)
    spec = _new_spec()
    (project / "music_spec.json").write_text(
        json.dumps(spec.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8"
    )
    (project / "versions" / "index.json").write_text(
        json.dumps(
            {
                "current_version_id": "v1",
                "versions": [
                    {
                        "version_id": "v1",
                        "version_number": 1,
                        "created_at": "2026-01-01T00:00:00Z",
                        "instruction": None,
                        "parent_version_id": None,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    ensure_version_layout(project)
    assert (project / "versions" / "v1" / "music_spec.json").exists()
    assert (project / "versions" / "v1" / "version_metadata.json").exists()
