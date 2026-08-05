"""T29：SoundFont 管理模块测试。"""

from packages.music_core.audio.soundfont_manager import (
    get_soundfont,
    list_soundfonts,
    resolve_default_soundfont,
    scan_soundfonts,
)


def test_empty_dir_scan_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUNDFONT_DIR", str(tmp_path))
    assert scan_soundfonts() == []


def test_sf2_and_sf3_are_scanned(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUNDFONT_DIR", str(tmp_path))
    (tmp_path / "FluidR3_GM.sf2").write_bytes(b"x" * 100)
    (tmp_path / "custom.sf3").write_bytes(b"y" * 50)
    fonts = scan_soundfonts()
    assert len(fonts) == 2
    assert {f.format for f in fonts} == {"sf2", "sf3"}


def test_non_soundfont_files_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUNDFONT_DIR", str(tmp_path))
    (tmp_path / "readme.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "note.mid").write_bytes(b"midi")
    (tmp_path / "real.sf2").write_bytes(b"x")
    assert len(scan_soundfonts()) == 1


def test_soundfont_id_is_stable(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUNDFONT_DIR", str(tmp_path))
    (tmp_path / "Stable.sf2").write_bytes(b"x")
    id1 = scan_soundfonts()[0].id
    id2 = scan_soundfonts()[0].id
    assert id1 == id2


def test_default_soundfont_selection_first_found(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUNDFONT_DIR", str(tmp_path))
    (tmp_path / "A.sf2").write_bytes(b"x")
    (tmp_path / "B.sf3").write_bytes(b"y")
    default = resolve_default_soundfont()
    assert default is not None
    assert default.name == "A"


def test_default_soundfont_id_override(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUNDFONT_DIR", str(tmp_path))
    (tmp_path / "A.sf2").write_bytes(b"x")
    (tmp_path / "B.sf3").write_bytes(b"y")
    fonts = scan_soundfonts()
    target = next(f for f in fonts if f.name == "B")
    monkeypatch.setenv("DEFAULT_SOUNDFONT_ID", target.id)
    default = resolve_default_soundfont()
    assert default is not None and default.id == target.id


def test_soundfont_path_override(tmp_path, monkeypatch):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "Custom.sf2").write_bytes(b"z")
    monkeypatch.setenv("SOUNDFONT_DIR", str(tmp_path))
    monkeypatch.setenv("SOUNDFONT_PATH", str(outside / "Custom.sf2"))
    fonts = list_soundfonts()
    assert any(f.name == "Custom" for f in fonts)
    default = resolve_default_soundfont()
    assert default is not None and default.name == "Custom"


def test_get_soundfont_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUNDFONT_DIR", str(tmp_path))
    assert get_soundfont("not-exist") is None


def test_tags_are_derived_from_filename(tmp_path, monkeypatch):
    monkeypatch.setenv("SOUNDFONT_DIR", str(tmp_path))
    (tmp_path / "orchestral_strings.sf2").write_bytes(b"x")
    font = scan_soundfonts()[0]
    assert "orchestral" in font.tags
    assert "strings" in font.tags
