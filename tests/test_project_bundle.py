"""工程导出/导入测试。"""

import json
import zipfile
from pathlib import Path

from packages.music_core.project_io.project_bundle import export_project_bundle
from packages.music_core.project_io.project_importer import import_project_bundle
from packages.music_core.validation.spec_validator import validate_music_spec
from services.api.schemas.music_spec import MusicSpec
from tests.test_harmony_engine import build_spec


def _make_project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    spec = build_spec()
    (project / "music_spec.json").write_text(
        json.dumps(spec.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )
    (project / "output.mid").write_bytes(b"MThd-test")
    (project / "mix_spec.json").write_text('{"version":"0.1"}', encoding="utf-8")
    (project / ".env").write_text("SECRET=1", encoding="utf-8")
    (project / "__pycache__").mkdir()
    (project / "__pycache__" / "x.pyc").write_bytes(b"x")
    return project, spec


def test_export_import_roundtrip(tmp_path):
    project, spec = _make_project(tmp_path)
    output = tmp_path / "song.aimusic.zip"
    export_project_bundle("song-1", project, output)
    assert output.exists()

    with zipfile.ZipFile(output) as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        assert "music_spec.json" in names
        assert not any(".env" in n for n in names)
        assert not any("__pycache__" in n for n in names)

    result = import_project_bundle(output, tmp_path / "projects")
    assert result["imported"] is True
    assert result["song_id"]
    imported_spec = MusicSpec.model_validate(
        json.loads((tmp_path / "projects" / result["song_id"] / "music_spec.json").read_text(encoding="utf-8"))
    )
    validate_music_spec(imported_spec)
    assert imported_spec.title == spec.title


def test_import_with_directory_entries(tmp_path):
    """zip 内目录项应被正确处理（创建目录，不当作文件写入）。"""
    spec = build_spec()
    bundle = tmp_path / "dirs.aimusic.zip"
    with zipfile.ZipFile(bundle, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"format": "ai-music-project", "song_id": "s1"}))
        zf.writestr("versions/", "")  # 目录项
        zf.writestr("versions/index.json", json.dumps({"current_version_id": None, "versions": []}))
        zf.writestr("music_spec.json", json.dumps(spec.model_dump(mode="json"), ensure_ascii=False))
    result = import_project_bundle(bundle, tmp_path / "projects")
    assert result["imported"] is True
    imported_dir = tmp_path / "projects" / result["song_id"]
    assert (imported_dir / "versions" / "index.json").exists()
    assert imported_dir.is_dir()


def test_zip_slip_rejected(tmp_path):
    evil_zip = tmp_path / "evil.aimusic.zip"
    with zipfile.ZipFile(evil_zip, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"format": "ai-music-project"}))
        zf.writestr("../evil.txt", "bad")
    try:
        import_project_bundle(evil_zip, tmp_path / "projects")
        assert False, "应当拒绝 zip slip"
    except ValueError:
        pass


def test_absolute_path_rejected(tmp_path):
    evil_zip = tmp_path / "abs.aimusic.zip"
    with zipfile.ZipFile(evil_zip, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"format": "ai-music-project"}))
        zf.writestr("/evil.txt", "bad")
    try:
        import_project_bundle(evil_zip, tmp_path / "projects")
        assert False, "应当拒绝绝对路径"
    except ValueError:
        pass


def test_wrong_format_rejected(tmp_path):
    bad_zip = tmp_path / "bad.aimusic.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"format": "other"}))
    try:
        import_project_bundle(bad_zip, tmp_path / "projects")
        assert False, "应当拒绝错误格式"
    except ValueError:
        pass


def _make_versioned_project(tmp_path: Path):
    """构造 v1+v2 目录式版本项目（v1: midi+mix；v2: midi+wav+mix+quality+stems+edit+diff）。"""
    project = tmp_path / "versioned"
    spec = build_spec()
    spec_data = spec.model_dump(mode="json")

    def write_json(path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    write_json(project / "music_spec.json", spec_data)
    write_json(project / "current.json", {"schema_version": 2, "current_version_id": "v2"})
    (project / "current_version_id.txt").write_text("v2", encoding="utf-8")

    v1 = project / "versions" / "v1"
    write_json(
        v1 / "version_metadata.json",
        {"version_id": "v1", "index": 1, "parent_version_id": None, "created_at": "2026-01-01T00:00:00Z", "kind": "initial", "path": "versions/v1"},
    )
    write_json(v1 / "music_spec.json", spec_data)
    (v1 / "output.mid").write_bytes(b"MThd-v1")
    write_json(v1 / "mix_spec.json", {"version": "0.1", "master_volume": 0.7})

    v2_spec = spec.model_copy(update={"tempo": spec.tempo.model_copy(update={"bpm": 82})})
    v2 = project / "versions" / "v2"
    write_json(
        v2 / "version_metadata.json",
        {"version_id": "v2", "index": 2, "parent_version_id": "v1", "created_at": "2026-01-02T00:00:00Z", "kind": "edit", "path": "versions/v2"},
    )
    write_json(v2 / "music_spec.json", v2_spec.model_dump(mode="json"))
    write_json(v2 / "edit_spec.json", {"instruction": "更快", "version": "0.1"})
    write_json(v2 / "diff.json", [{"field": "tempo.bpm", "old": 72, "new": 82}])
    (v2 / "output.mid").write_bytes(b"MThd-v2")
    (v2 / "output.wav").write_bytes(b"RIFF-v2")
    write_json(v2 / "audio_metadata.json", {"renderer": "fallback", "sample_rate": 44100})
    write_json(v2 / "mix_spec.json", {"version": "0.1", "master_volume": 0.8})
    write_json(v2 / "quality_report.json", {"score": 85})
    (v2 / "stems").mkdir()
    (v2 / "stems" / "melody.mid").write_bytes(b"stem")

    # 根目录当前版本镜像（v2）
    (project / "output.mid").write_bytes(b"MThd-v2")
    (project / "output.wav").write_bytes(b"RIFF-v2")
    write_json(project / "audio_metadata.json", {"renderer": "fallback", "sample_rate": 44100})
    write_json(project / "mix_spec.json", {"version": "0.1", "master_volume": 0.8})
    write_json(project / "quality_report.json", {"score": 85})
    (project / "stems").mkdir()
    (project / "stems" / "melody.mid").write_bytes(b"stem")
    write_json(project / "soundfont.json", {"soundfont_id": "missing-sf", "renderer": "fluidsynth"})

    index = {
        "schema_version": 2,
        "current_version_id": "v2",
        "versions": [
            {
                "version_id": "v1",
                "version_number": 1,
                "index": 1,
                "created_at": "2026-01-01T00:00:00Z",
                "instruction": None,
                "parent_version_id": None,
                "kind": "initial",
                "path": "versions/v1",
            },
            {
                "version_id": "v2",
                "version_number": 2,
                "index": 2,
                "created_at": "2026-01-02T00:00:00Z",
                "instruction": "更快",
                "parent_version_id": "v1",
                "kind": "edit",
                "path": "versions/v2",
            },
        ],
    }
    write_json(project / "versions" / "index.json", index)
    return project, v2_spec


def test_export_v2_bundle_contains_versioned_assets(tmp_path):
    project, _ = _make_versioned_project(tmp_path)
    output = tmp_path / "v2.aimusic.zip"
    export_project_bundle("orig-song-id", project, output)

    with zipfile.ZipFile(output) as zf:
        names = set(zf.namelist())
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["bundle_format"] == "aimusic"
        assert manifest["bundle_version"] == 2
        assert manifest["source_song_id"] == "orig-song-id"
        assert manifest["current_version_id"] == "v2"
        assert len(manifest["versions"]) == 2
        assert manifest["versions"][0]["path"] == "versions/v1"
        assert manifest["assets"]["has_soundfont_config"] is True

        assert "versions/index.json" in names
        assert "versions/v1/version_metadata.json" in names
        assert "versions/v1/music_spec.json" in names
        assert "versions/v1/output.mid" in names
        assert "versions/v2/music_spec.json" in names
        assert "versions/v2/edit_spec.json" in names
        assert "versions/v2/diff.json" in names
        assert "versions/v2/output.mid" in names
        assert "versions/v2/output.wav" in names
        assert "versions/v2/audio_metadata.json" in names
        assert "versions/v2/quality_report.json" in names
        assert "versions/v2/stems/melody.mid" in names
        assert "soundfont.json" in names
        assert not any(".env" in n for n in names)
        assert not any("llm_calls" in n for n in names)
        assert not any("tasks" in n or "evaluations" in n for n in names)


def test_import_v2_bundle_restores_versions_and_mirror(tmp_path):
    project, v2_spec = _make_versioned_project(tmp_path)
    output = tmp_path / "v2.aimusic.zip"
    export_project_bundle("orig-song-id", project, output)

    result = import_project_bundle(output, tmp_path / "projects")
    assert result["imported"] is True
    assert result["source_song_id"] == "orig-song-id"
    assert result["current_version_id"] == "v2"
    assert result["version_count"] == 2
    assert result["assets"]["has_midi"] is True
    assert result["assets"]["has_audio"] is True
    assert result["assets"]["has_stems"] is True
    assert result["assets"]["has_soundfont_config"] is True

    root = tmp_path / "projects" / result["song_id"]
    index = json.loads((root / "versions" / "index.json").read_text(encoding="utf-8"))
    assert index["current_version_id"] == "v2"
    assert len(index["versions"]) == 2
    assert (root / "current_version_id.txt").read_text(encoding="utf-8") == "v2"
    assert (root / "versions" / "v1" / "version_metadata.json").exists()
    assert (root / "versions" / "v1" / "music_spec.json").exists()
    assert (root / "versions" / "v1" / "output.mid").exists()
    assert (root / "versions" / "v2" / "edit_spec.json").exists()
    assert (root / "versions" / "v2" / "diff.json").exists()
    assert (root / "versions" / "v2" / "output.wav").exists()

    # 根目录镜像与当前版本一致
    root_spec = json.loads((root / "music_spec.json").read_text(encoding="utf-8"))
    v2_spec_data = json.loads((root / "versions" / "v2" / "music_spec.json").read_text(encoding="utf-8"))
    assert root_spec == v2_spec_data
    assert root_spec["tempo"]["bpm"] == 82
    assert (root / "output.mid").read_bytes() == b"MThd-v2"
    assert (root / "output.wav").exists()
    assert (root / "stems" / "melody.mid").exists()


def test_import_twice_generates_different_song_ids(tmp_path):
    project, _ = _make_versioned_project(tmp_path)
    output = tmp_path / "twice.aimusic.zip"
    export_project_bundle("orig-song-id", project, output)

    first = import_project_bundle(output, tmp_path / "projects")
    second = import_project_bundle(output, tmp_path / "projects")
    assert first["song_id"] != second["song_id"]
    assert (tmp_path / "projects" / first["song_id"]).exists()
    assert (tmp_path / "projects" / second["song_id"]).exists()


def test_import_legacy_bundle_with_versions_json_migrates(tmp_path):
    """旧版 bundle（versions/v1.json）导入后自动迁移为目录式版本结构。"""
    spec = build_spec()
    bundle = tmp_path / "legacy.aimusic.zip"
    with zipfile.ZipFile(bundle, "w") as zf:
        zf.writestr(
            "manifest.json",
            json.dumps({"format": "ai-music-project", "format_version": "0.1", "song_id": "old-id"}),
        )
        zf.writestr("music_spec.json", json.dumps(spec.model_dump(mode="json"), ensure_ascii=False))
        zf.writestr(
            "versions/index.json",
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
                }
            ),
        )
        zf.writestr(
            "versions/v1.json",
            json.dumps(
                {
                    "version_id": "v1",
                    "version_number": 1,
                    "created_at": "2026-01-01T00:00:00Z",
                    "instruction": None,
                    "parent_version_id": None,
                    "music_spec": spec.model_dump(mode="json"),
                },
                ensure_ascii=False,
            ),
        )
        zf.writestr("output.mid", b"MThd-legacy")

    result = import_project_bundle(bundle, tmp_path / "projects")
    root = tmp_path / "projects" / result["song_id"]
    assert result["version_count"] == 1
    assert (root / "versions" / "v1" / "version_metadata.json").exists()
    assert (root / "versions" / "v1" / "music_spec.json").exists()
    assert (root / "current_version_id.txt").read_text(encoding="utf-8") == "v1"
    assert (root / "output.mid").exists()
