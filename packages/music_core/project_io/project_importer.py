"""工程导入：.aimusic.zip → 新的项目目录（支持 v2 目录式版本与旧版 bundle）。"""

from __future__ import annotations

import json
import logging
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from packages.music_core.project_io.project_bundle import BUNDLE_FORMAT, BUNDLE_VERSION
from packages.music_core.validation.spec_validator import validate_music_spec
from packages.music_core.versioning.version_assets import restore_version_assets_to_current
from packages.music_core.versioning.version_migration import (
    MUSIC_SPEC_FILE,
    VERSION_METADATA_FILE,
    ensure_version_layout,
)

logger = logging.getLogger(__name__)


def _safe_extract_target(projects_root: Path, new_song_id: str, name: str) -> Path:
    """校验 zip 内路径并返回安全的解压目标（跨平台防 zip slip）。"""
    path = Path(name)
    if path.is_absolute():
        raise ValueError(f"非法绝对路径：{name}")
    target_root = (projects_root / new_song_id).resolve()
    try:
        target = (target_root / path).resolve()
        target.relative_to(target_root)
    except ValueError as exc:
        raise ValueError(f"路径越界：{name}") from exc
    return target


def _read_manifest(zf: zipfile.ZipFile) -> dict:
    """读取并校验 manifest；返回 manifest dict。"""
    names = set(zf.namelist())
    if "manifest.json" not in names:
        raise ValueError("缺少 manifest.json，不是有效的 .aimusic.zip")
    manifest = json.loads(zf.read("manifest.json"))
    # 新版：bundle_format == aimusic / bundle_version == 2
    if manifest.get("bundle_format") == BUNDLE_FORMAT and manifest.get("bundle_version") == BUNDLE_VERSION:
        return manifest
    # 旧版：format == ai-music-project / format_version == 0.1
    if manifest.get("format") == "ai-music-project" and manifest.get("format_version") in ("0.1", None):
        return manifest
    raise ValueError(f"不支持的工程格式：{json.dumps(manifest, ensure_ascii=False)[:120]}")


def _init_v1_from_root_spec(project_dir: Path) -> None:
    """旧 bundle 无 versions 时：以根目录 music_spec.json 初始化 v1 目录式版本。"""
    spec_path = project_dir / "music_spec.json"
    if not spec_path.exists():
        raise ValueError("缺少 music_spec.json")
    spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
    versions_dir = project_dir / "versions"
    v1_dir = versions_dir / "v1"
    v1_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    metadata = {
        "version_id": "v1",
        "index": 1,
        "parent_version_id": None,
        "created_at": now,
        "kind": "initial",
        "prompt": spec_data.get("prompt"),
        "edit_instruction": None,
        "notes": None,
        "path": "versions/v1",
    }
    (v1_dir / VERSION_METADATA_FILE).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (v1_dir / MUSIC_SPEC_FILE).write_text(
        json.dumps(spec_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    index = {
        "schema_version": 2,
        "current_version_id": "v1",
        "versions": [
            {
                "version_id": "v1",
                "version_number": 1,
                "index": 1,
                "created_at": now,
                "instruction": None,
                "edit_instruction": None,
                "parent_version_id": None,
                "kind": "initial",
                "prompt": spec_data.get("prompt"),
                "notes": None,
                "path": "versions/v1",
            }
        ],
    }
    (versions_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (project_dir / "current_version_id.txt").write_text("v1", encoding="utf-8")
    (project_dir / "current.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "current_version_id": "v1",
                "updated_at": now,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _import_summary(project_dir: Path, source_manifest: dict) -> dict:
    """从导入后的项目目录与来源 manifest 组装导入摘要。"""
    root_flags = {
        "has_midi": (project_dir / "output.mid").exists(),
        "has_audio": (project_dir / "output.wav").exists(),
        "has_mix": (project_dir / "mix_spec.json").exists(),
        "has_quality_report": (project_dir / "quality_report.json").exists(),
        "has_stems": (project_dir / "stems").exists() and (project_dir / "stems").is_dir(),
        "has_soundfont_config": (project_dir / "soundfont.json").exists(),
    }
    index_path = project_dir / "versions" / "index.json"
    current_version_id: str | None = None
    version_count = 0
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
        current_version_id = index.get("current_version_id")
        version_count = len(index.get("versions", []))
    else:
        current_version_id = source_manifest.get("current_version_id")
        version_count = len(source_manifest.get("versions", []))

    spec_path = project_dir / "music_spec.json"
    try:
        spec = validate_music_spec(json.loads(spec_path.read_text(encoding="utf-8")))
        tracks = len(spec.tracks)
        bars = spec.length.bars
    except Exception:  # noqa: BLE001 - 摘要尽量不因可选信息失败
        tracks = 0
        bars = 0

    return {
        "tracks": tracks,
        "bars": bars,
        "files": 0,
        "version_count": version_count,
        "current_version_id": current_version_id,
        "has_versions": (project_dir / "versions" / "index.json").exists(),
        "has_midi": root_flags["has_midi"],
        "has_audio": root_flags["has_audio"],
        "has_mix": root_flags["has_mix"],
        "has_quality_report": root_flags["has_quality_report"],
        "has_stems": root_flags["has_stems"],
        "has_soundfont_config": root_flags["has_soundfont_config"],
    }


def import_project_bundle(bundle_path: Path, projects_root: Path) -> dict:
    """导入 .aimusic.zip 到新的 song_id 目录（防 zip slip，不覆盖已有项目）。"""
    projects_root = Path(projects_root)
    projects_root.mkdir(parents=True, exist_ok=True)
    new_song_id = str(uuid.uuid4())
    target_root = (projects_root / new_song_id).resolve()

    try:
        zf = zipfile.ZipFile(bundle_path, "r")
    except zipfile.BadZipFile as exc:
        raise ValueError("不是有效的 zip 文件") from exc

    try:
        with zf:
            manifest = _read_manifest(zf)
            for info in zf.infolist():
                name = info.filename
                if info.is_dir() or name.endswith("/"):
                    _safe_extract_target(projects_root, new_song_id, name).mkdir(
                        parents=True, exist_ok=True
                    )
                    continue
                target = _safe_extract_target(projects_root, new_song_id, name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(name))

        # 迁移 / 初始化目录式版本布局（旧版 bundle 自动迁移）
        ensure_version_layout(target_root)
        index_path = target_root / "versions" / "index.json"
        index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else None
        if index is None or not index.get("versions"):
            # 旧 bundle 完全没有 versions 时，以根目录 spec 初始化 v1
            _init_v1_from_root_spec(target_root)
        else:
            current_version_id = index.get("current_version_id")
            version_dir = None
            if current_version_id:
                candidate = target_root / "versions" / current_version_id
                if candidate.is_dir():
                    version_dir = candidate
            if version_dir is None:
                # 从 index 取第一个版本目录
                for entry in index.get("versions", []):
                    number = int(entry.get("version_number") or entry.get("index") or 1)
                    candidate = target_root / "versions" / f"v{number}"
                    if candidate.is_dir():
                        version_dir = candidate
                        current_version_id = entry.get("version_id") or f"v{number}"
                        break
            if version_dir is None:
                raise ValueError("bundle 缺少版本目录（versions/vN/）")
            if not (version_dir / "music_spec.json").exists():
                raise ValueError(f"当前版本 {current_version_id} 缺少 music_spec.json")
            # 以当前版本目录为准修复根目录镜像（不重新生成 MIDI/WAV）
            restore_version_assets_to_current(target_root, version_dir)

        # 根目录 music_spec.json 必须存在
        spec_path = target_root / "music_spec.json"
        if not spec_path.exists():
            raise ValueError("缺少 music_spec.json")
        validate_music_spec(json.loads(spec_path.read_text(encoding="utf-8")))

        summary = _import_summary(target_root, manifest)
        return {
            "song_id": new_song_id,
            "imported": True,
            "source_song_id": manifest.get("source_song_id"),
            "current_version_id": summary["current_version_id"],
            "version_count": summary["version_count"],
            "assets": {
                "has_midi": summary["has_midi"],
                "has_audio": summary["has_audio"],
                "has_mix": summary["has_mix"],
                "has_quality_report": summary["has_quality_report"],
                "has_stems": summary["has_stems"],
                "has_soundfont_config": summary["has_soundfont_config"],
            },
            "warnings": [],
            "summary": summary,
        }
    except Exception:
        # 导入失败：清理半成品项目目录
        if target_root.exists():
            shutil.rmtree(target_root, ignore_errors=True)
        raise
