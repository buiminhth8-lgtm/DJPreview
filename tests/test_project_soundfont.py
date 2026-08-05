"""T29：项目级音源设置保存 / 恢复版本不破坏。"""

import json

from services.api.storage import project_store
from services.api.storage.project_store import (
    create_project,
    create_version,
    get_project_soundfont,
    restore_version,
    save_project_soundfont,
)
from tests.test_harmony_engine import build_spec


def _setup(tmp_path, monkeypatch):
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    settings = type("Settings", (), {"projects_dir": projects_dir})()
    monkeypatch.setattr(project_store, "get_settings", lambda: settings)
    return projects_dir


def test_save_and_read_project_soundfont(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    song_id = create_project(build_spec())
    assert get_project_soundfont(song_id) is None

    data = {"soundfont_id": "abc", "soundfont_name": "Demo", "renderer": "auto"}
    save_project_soundfont(song_id, data)
    saved = get_project_soundfont(song_id)
    assert saved == data
    path = tmp_path / "projects" / song_id / "soundfont.json"
    assert json.loads(path.read_text(encoding="utf-8")) == data


def test_restore_version_does_not_clobber_soundfont(tmp_path, monkeypatch):
    projects = _setup(tmp_path, monkeypatch)
    song_id = create_project(build_spec())
    save_project_soundfont(song_id, {"soundfont_id": "keep-me", "soundfont_name": "Keep", "renderer": "auto"})

    base = build_spec()
    new_spec = base.model_copy(update={"tempo": base.tempo.model_copy(update={"bpm": 82})})
    create_version(song_id, new_spec, "更快", None)
    restore_version(song_id, "v1")

    assert get_project_soundfont(song_id)["soundfont_id"] == "keep-me"
    assert (projects / song_id / "soundfont.json").exists()
