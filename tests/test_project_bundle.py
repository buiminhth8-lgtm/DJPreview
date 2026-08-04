"""工程导出/导入测试。"""

import json
import zipfile

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


def test_wrong_format_rejected(tmp_path):
    bad_zip = tmp_path / "bad.aimusic.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"format": "other"}))
    try:
        import_project_bundle(bad_zip, tmp_path / "projects")
        assert False, "应当拒绝错误格式"
    except ValueError:
        pass
