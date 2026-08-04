""".aimusic.zip 导入 zip slip 路径安全专项测试（跨平台）。"""

import json
import zipfile
from pathlib import Path

import pytest

from packages.music_core.project_io.project_importer import import_project_bundle
from tests.test_harmony_engine import build_spec

# 恶意路径矩阵（Windows / Linux / macOS 通用判断）
MALICIOUS_NAMES = [
    "../evil.txt",
    "../../evil.txt",
    "/absolute/evil.txt",
    r"C:\evil.txt",
    "versions/../../evil.txt",
]


def _build_zip(bundle: Path, name: str, valid_spec: bool = False) -> Path:
    with zipfile.ZipFile(bundle, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"format": "ai-music-project", "song_id": "s1"}))
        if valid_spec:
            spec = build_spec()
            zf.writestr("music_spec.json", json.dumps(spec.model_dump(mode="json"), ensure_ascii=False))
        zf.writestr(name, "evil")
    return bundle


@pytest.mark.parametrize("name", MALICIOUS_NAMES)
def test_malicious_path_rejected_or_contained(tmp_path, name):
    """恶意路径必须被拒绝，且 evil.txt 绝不能出现在 projects_root 外部。"""
    projects_root = tmp_path / "projects"
    bundle = _build_zip(tmp_path / "evil.aimusic.zip", name)
    try:
        import_project_bundle(bundle, projects_root)
    except ValueError:
        pass
    else:
        # 某些平台（如 POSIX 上 "C:\evil.txt"）可能被当作相对文件名写入，
        # 但绝不允许写入 projects_root 之外。
        for candidate in tmp_path.rglob("evil.txt"):
            try:
                candidate.resolve().relative_to(projects_root.resolve())
            except ValueError:
                pytest.fail(f"evil.txt 被写入 projects_root 外部：{candidate}")


def test_escape_variants_raise_value_error(tmp_path):
    """四个明确的逃逸/绝对路径写法在任何平台都必须抛 ValueError。"""
    variants = ["../evil.txt", "../../evil.txt", "/absolute/evil.txt", "versions/../../evil.txt"]
    for i, name in enumerate(variants):
        projects_root = tmp_path / f"projects_{i}"
        bundle = _build_zip(tmp_path / f"evil_{i}.aimusic.zip", name)
        with pytest.raises(ValueError):
            import_project_bundle(bundle, projects_root)
        assert not (projects_root.parent / "evil.txt").exists()


def test_valid_import_keeps_files_inside(tmp_path):
    """合法 zip 导入后，所有文件都落在新 song_id 目录内。"""
    projects_root = tmp_path / "projects"
    bundle = _build_zip(tmp_path / "valid.aimusic.zip", "notes.txt", valid_spec=True)
    result = import_project_bundle(bundle, projects_root)
    root = (projects_root / result["song_id"]).resolve()
    for path in projects_root.rglob("*"):
        if path.is_file():
            assert path.resolve().is_relative_to(root), f"文件越界：{path}"
