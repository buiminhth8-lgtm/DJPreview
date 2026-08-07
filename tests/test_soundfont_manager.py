"""T29：SoundFont 管理模块测试。"""

from pathlib import Path

from packages.music_core.audio.soundfont_manager import (
    get_soundfont,
    list_soundfonts,
    resolve_default_soundfont,
    scan_soundfonts,
)


def _isolate_scan(tmp_path, monkeypatch):
    """把扫描目录隔离到 tmp_path，避免仓库内真实音源（如 GeneralUser-GS.sf2）干扰。"""
    monkeypatch.setenv("SOUNDFONT_DIR", str(tmp_path))
    monkeypatch.setattr(
        "packages.music_core.audio.soundfont_manager._scan_dirs",
        lambda: [Path(tmp_path)],
    )


def test_empty_dir_scan_returns_empty_list(tmp_path, monkeypatch):
    _isolate_scan(tmp_path, monkeypatch)
    assert scan_soundfonts() == []


def test_sf2_and_sf3_are_scanned(tmp_path, monkeypatch):
    _isolate_scan(tmp_path, monkeypatch)
    (tmp_path / "FluidR3_GM.sf2").write_bytes(b"x" * 100)
    (tmp_path / "custom.sf3").write_bytes(b"y" * 50)
    fonts = scan_soundfonts()
    assert len(fonts) == 2
    assert {f.format for f in fonts} == {"sf2", "sf3"}


def test_non_soundfont_files_ignored(tmp_path, monkeypatch):
    _isolate_scan(tmp_path, monkeypatch)
    (tmp_path / "readme.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "note.mid").write_bytes(b"midi")
    (tmp_path / "real.sf2").write_bytes(b"x")
    assert len(scan_soundfonts()) == 1


def test_soundfont_id_is_stable(tmp_path, monkeypatch):
    _isolate_scan(tmp_path, monkeypatch)
    (tmp_path / "Stable.sf2").write_bytes(b"x")
    id1 = scan_soundfonts()[0].id
    id2 = scan_soundfonts()[0].id
    assert id1 == id2


def test_default_soundfont_selection_first_found(tmp_path, monkeypatch):
    _isolate_scan(tmp_path, monkeypatch)
    (tmp_path / "A.sf2").write_bytes(b"x")
    (tmp_path / "B.sf3").write_bytes(b"y")
    default = resolve_default_soundfont()
    assert default is not None
    assert default.name == "A"


def test_default_soundfont_id_override(tmp_path, monkeypatch):
    _isolate_scan(tmp_path, monkeypatch)
    (tmp_path / "A.sf2").write_bytes(b"x")
    (tmp_path / "B.sf3").write_bytes(b"y")
    fonts = scan_soundfonts()
    target = next(f for f in fonts if f.name == "B")
    monkeypatch.setenv("DEFAULT_SOUNDFONT_ID", target.id)
    default = resolve_default_soundfont()
    assert default is not None and default.id == target.id


def test_soundfont_path_override(tmp_path, monkeypatch):
    _isolate_scan(tmp_path, monkeypatch)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "Custom.sf2").write_bytes(b"z")
    monkeypatch.setenv("SOUNDFONT_PATH", str(outside / "Custom.sf2"))
    fonts = list_soundfonts()
    assert any(f.name == "Custom" for f in fonts)
    default = resolve_default_soundfont()
    assert default is not None and default.name == "Custom"


def test_get_soundfont_missing_returns_none(tmp_path, monkeypatch):
    _isolate_scan(tmp_path, monkeypatch)
    assert get_soundfont("not-exist") is None


def test_tags_are_derived_from_filename(tmp_path, monkeypatch):
    _isolate_scan(tmp_path, monkeypatch)
    (tmp_path / "orchestral_strings.sf2").write_bytes(b"x")
    font = scan_soundfonts()[0]
    assert "orchestral" in font.tags
    assert "strings" in font.tags
