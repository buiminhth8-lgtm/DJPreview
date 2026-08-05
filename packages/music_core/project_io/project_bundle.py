"""工程导出：项目目录 → .aimusic.zip（bundle_version=2，目录式版本资产）。"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from packages.music_core.versioning.version_migration import ensure_version_layout

_APP_VERSION = "stage-6-v0.1"

BUNDLE_FORMAT = "aimusic"
BUNDLE_VERSION = 2

# 不在 zip 中出现的目录 / 文件（绝对避免敏感或生成数据）
_EXCLUDED_DIRS = {
    "llm_calls",
    "tasks",
    "evaluations",
    "exports",
    "node_modules",
    "dist",
    "__pycache__",
}
_EXCLUDED_FILE_SUFFIXES = (".tmp", "~", ".pyc")
_EXCLUDED_FILENAMES = {".env", ".env.docker"}

# 受版本管理的资产文件名（versions/vN/ 内）
_VERSION_ASSET_FILES = (
    "music_spec.json",
    "output.mid",
    "output.wav",
    "audio_metadata.json",
    "mix_spec.json",
    "quality_report.json",
    "optimize_report.json",
    "edit_spec.json",
    "diff.json",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_excluded(path: Path) -> bool:
    """判断路径是否属于不应打包的目录 / 文件。"""
    if path.is_dir():
        return path.name in _EXCLUDED_DIRS
    return (
        path.name in _EXCLUDED_FILENAMES
        or path.suffix.lower() in _EXCLUDED_FILE_SUFFIXES
        or path.name.endswith(".aimusic.zip")
    )


def _version_asset_flags(version_dir: Path) -> dict[str, bool]:
    """收集 versions/vN/ 内的资产存在状态（不要求存在）。"""
    return {
        "has_music_spec": (version_dir / "music_spec.json").exists(),
        "has_midi": (version_dir / "output.mid").exists(),
        "has_audio": (version_dir / "output.wav").exists(),
        "has_audio_metadata": (version_dir / "audio_metadata.json").exists(),
        "has_mix": (version_dir / "mix_spec.json").exists(),
        "has_quality_report": (version_dir / "quality_report.json").exists(),
        "has_stems": (version_dir / "stems").exists() and (version_dir / "stems").is_dir(),
        "has_edit_spec": (version_dir / "edit_spec.json").exists(),
        "has_diff": (version_dir / "diff.json").exists(),
    }


def _root_asset_flags(project_dir: Path) -> dict[str, bool]:
    """收集根目录当前版本镜像的资产存在状态。"""
    return {
        "has_midi": (project_dir / "output.mid").exists(),
        "has_audio": (project_dir / "output.wav").exists(),
        "has_mix": (project_dir / "mix_spec.json").exists(),
        "has_quality_report": (project_dir / "quality_report.json").exists(),
        "has_stems": (project_dir / "stems").exists() and (project_dir / "stems").is_dir(),
        "has_soundfont_config": (project_dir / "soundfont.json").exists(),
    }


def _collect_zip_entries(project_dir: Path) -> list[tuple[Path, str]]:
    """收集需要打包的 (源路径, zip 内 POSIX 相对路径)，排除敏感内容。"""
    entries: list[tuple[Path, str]] = []
    for src in sorted(project_dir.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(project_dir).as_posix()
        if _is_excluded(src):
            continue
        if any(part in _EXCLUDED_DIRS for part in src.relative_to(project_dir).parts[:-1]):
            continue
        entries.append((src, rel))
    return entries


def build_manifest(song_id: str, project_dir: Path) -> dict:
    """构建 v2 manifest（含版本清单与资产状态）。"""
    project_dir = Path(project_dir)
    ensure_version_layout(project_dir)

    versions_dir = project_dir / "versions"
    index_path = versions_dir / "index.json"
    versions: list[dict] = []
    current_version_id: str | None = None
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
        current_version_id = index.get("current_version_id")
        for entry in index.get("versions", []):
            number = int(entry.get("version_number") or entry.get("index") or 1)
            vdir = versions_dir / f"v{number}"
            version_id = entry.get("version_id") or f"v{number}"
            versions.append(
                {
                    "version_id": version_id,
                    "version_number": number,
                    "path": f"versions/v{number}",
                    **{k: v for k, v in _version_asset_flags(vdir).items()},
                }
            )
    else:
        current_version_id = None

    return {
        "bundle_format": BUNDLE_FORMAT,
        "bundle_version": BUNDLE_VERSION,
        "exported_at": _now_iso(),
        "source_song_id": song_id,
        "project_schema_version": 2,
        "app_version": _APP_VERSION,
        "current_version_id": current_version_id,
        "versions": versions,
        "assets": _root_asset_flags(project_dir),
    }


def export_project_bundle(song_id: str, project_dir: Path, output_path: Path) -> Path:
    """导出 .aimusic.zip（bundle_version=2）。

    包含：manifest.json、根目录当前版本镜像（music_spec / current.json /
    current_version_id.txt / 可选资产）、完整 versions/vN/ 目录式版本资产。
    不包含：.env、llm_calls / tasks / evaluations、真实 SoundFont、临时文件。
    """
    project_dir = Path(project_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(song_id, project_dir)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for src, rel in _collect_zip_entries(project_dir):
            zf.write(src, rel)
    return output_path
