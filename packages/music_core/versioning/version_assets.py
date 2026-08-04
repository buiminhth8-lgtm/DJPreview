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

# 受版本管理的资产清单（恢复时从版本目录复制到根目录当前镜像；
# 版本目录缺失的项会清理根目录旧资产）
MANAGED_VERSION_ASSETS = (
    "music_spec.json",
    "output.mid",
    "output.wav",
    "audio_metadata.json",
    "mix_spec.json",
    "quality_report.json",
    STEMS_DIR_NAME,
)


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


def _remove_path(path: Path) -> None:
    """删除文件或目录（名称固定、由调用方限定，不做通配）。"""
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def restore_version_assets_to_current(project_dir: Path | str, version_dir: Path | str) -> dict:
    """从版本目录恢复资产到项目根目录当前版本镜像。

    规则：
    1. 版本目录中存在的文件/目录复制到根目录（文件 copy2，目录安全递归复制）；
    2. 版本目录中缺失的可选资产，清理根目录同名旧资产；
    3. music_spec.json 为必须项，缺失抛 FileNotFoundError；
    4. 不复制 llm_calls / 临时文件 / .env / 整个 versions 目录。

    返回：{"restored": [...], "removed": [...], "missing_optional": [...]}
    """
    project_dir = Path(project_dir)
    version_dir = Path(version_dir)
    if not project_dir.exists() or not project_dir.is_dir():
        raise FileNotFoundError(f"项目目录不存在：{project_dir}")
    if not version_dir.exists() or not version_dir.is_dir():
        raise FileNotFoundError(f"版本目录不存在：{version_dir}")
    if not (version_dir / "music_spec.json").exists():
        raise FileNotFoundError(f"版本目录缺少 music_spec.json：{version_dir}")

    restored: list[str] = []
    removed: list[str] = []
    missing_optional: list[str] = []

    for name in MANAGED_VERSION_ASSETS:
        src = version_dir / name
        target = project_dir / name
        if name == STEMS_DIR_NAME:
            if src.exists() and src.is_dir():
                _remove_path(target)
                _copy_tree_skip_temp(src, target)
                restored.append(name)
            else:
                if target.exists():
                    _remove_path(target)
                    removed.append(name)
                else:
                    missing_optional.append(name)
            continue
        if src.exists() and src.is_file():
            shutil.copy2(src, target)
            restored.append(name)
        else:
            if target.exists():
                _remove_path(target)
                removed.append(name)
            else:
                missing_optional.append(name)

    return {
        "restored": restored,
        "removed": removed,
        "missing_optional": missing_optional,
    }
