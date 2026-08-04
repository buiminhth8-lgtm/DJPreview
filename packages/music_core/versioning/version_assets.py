"""版本资产同步工具（T12）：根目录 ↔ 版本目录的资产复制。"""

from __future__ import annotations

import shutil
from pathlib import Path

# 需要同步的顶层资产文件（存在才复制）
ASSET_FILES = (
    "output.mid",
    "output.wav",
    "audio_metadata.json",
    "mix_spec.json",
    "quality_report.json",
    "optimize_report.json",
)

STEMS_DIR_NAME = "stems"


def _copy_tree_skip_temp(src: Path, dst: Path) -> None:
    """安全复制目录树，跳过临时文件（*.tmp / *~）。"""
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name.endswith(".tmp") or item.name.endswith("~"):
            continue
        target = dst / item.name
        if item.is_dir():
            _copy_tree_skip_temp(item, target)
        else:
            shutil.copy2(item, target)


def copy_current_assets_to_version(project_dir: Path | str, version_dir: Path | str) -> None:
    """把项目根目录的当前版本镜像资产复制到版本目录（存在才复制，可重复执行）。"""
    project_dir = Path(project_dir)
    version_dir = Path(version_dir)
    version_dir.mkdir(parents=True, exist_ok=True)
    for name in ASSET_FILES:
        src = project_dir / name
        if src.exists() and src.is_file():
            shutil.copy2(src, version_dir / name)
    stems_src = project_dir / STEMS_DIR_NAME
    if stems_src.exists() and stems_src.is_dir():
        _copy_tree_skip_temp(stems_src, version_dir / STEMS_DIR_NAME)


def mirror_stems_to_root(version_stems_dir: Path | str, root_stems_dir: Path | str) -> None:
    """把版本目录的 stems/ 镜像到项目根目录（保持旧接口可用）。"""
    version_stems_dir = Path(version_stems_dir)
    root_stems_dir = Path(root_stems_dir)
    if version_stems_dir.exists() and version_stems_dir.is_dir():
        _copy_tree_skip_temp(version_stems_dir, root_stems_dir)
