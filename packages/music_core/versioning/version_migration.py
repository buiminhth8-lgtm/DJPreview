"""版本结构懒迁移：旧 vN.json 快照 → 目录式 versions/vN/（schema_version=2）。"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from packages.music_core.versioning.version_assets import copy_current_assets_to_version

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 2
INDEX_FILE = "index.json"
VERSION_METADATA_FILE = "version_metadata.json"
MUSIC_SPEC_FILE = "music_spec.json"
EDIT_SPEC_FILE = "edit_spec.json"
DIFF_FILE = "diff.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _version_dir(versions_dir: Path, number: int) -> Path:
    return versions_dir / f"v{number}"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _canonical_version_id(version_id: str | None, number: int) -> str:
    """版本 id 规范化为 vN；已是 vN 则原样保留。"""
    if version_id and version_id.lower() == f"v{number}":
        return version_id
    return f"v{number}"


def _migrate_one_version(
    project_dir: Path,
    versions_dir: Path,
    number: int,
    entry: dict,
    current_version_id: str | None,
) -> str:
    """把单个版本迁移为 versions/vN/；返回规范化 version_id。"""
    target_dir = _version_dir(versions_dir, number)
    version_id = _canonical_version_id(entry.get("version_id"), number)
    metadata = {
        "version_id": version_id,
        "index": number,
        "parent_version_id": entry.get("parent_version_id"),
        "created_at": entry.get("created_at") or _now_iso(),
        "kind": entry.get("kind") or ("initial" if number == 1 else "edit"),
        "prompt": entry.get("prompt"),
        "edit_instruction": entry.get("edit_instruction") or entry.get("instruction"),
        "notes": entry.get("notes"),
        "path": f"versions/v{number}",
    }
    music_spec: dict | None = None
    edit_spec = entry.get("edit_spec")
    diff = entry.get("diff")

    if target_dir.is_dir() and (target_dir / VERSION_METADATA_FILE).exists():
        # 已迁移：只补齐缺失文件，不覆盖已有数据
        if (target_dir / MUSIC_SPEC_FILE).exists():
            return version_id
        music_spec = None
    else:
        # 旧 vN.json 快照
        legacy = versions_dir / f"v{number}.json"
        if legacy.exists():
            try:
                snapshot = _read_json(legacy)
                music_spec = snapshot.get("music_spec")
                edit_spec = snapshot.get("edit_spec")
                diff = snapshot.get("diff")
                metadata["parent_version_id"] = snapshot.get("parent_version_id")
                metadata["created_at"] = snapshot.get("created_at") or metadata["created_at"]
                metadata["kind"] = snapshot.get("kind") or metadata["kind"]
                metadata["edit_instruction"] = snapshot.get("instruction")
                metadata["notes"] = snapshot.get("notes")
            except Exception:  # noqa: BLE001 - 旧文件损坏时回退根目录
                logger.warning("旧版本快照 %s 读取失败，回退根目录 music_spec.json", legacy)

    target_dir.mkdir(parents=True, exist_ok=True)
    _write_json(target_dir / VERSION_METADATA_FILE, metadata)
    if music_spec is None and (project_dir / MUSIC_SPEC_FILE).exists():
        # 当前版本或仅剩根目录 spec 时，用根目录镜像兜底
        music_spec = _read_json(project_dir / MUSIC_SPEC_FILE)
        metadata["prompt"] = music_spec.get("prompt")
        _write_json(target_dir / VERSION_METADATA_FILE, metadata)
    if music_spec is not None:
        _write_json(target_dir / MUSIC_SPEC_FILE, music_spec)
    if edit_spec is not None:
        _write_json(target_dir / EDIT_SPEC_FILE, edit_spec)
    if diff is not None:
        _write_json(target_dir / DIFF_FILE, diff)

    # 当前版本资产镜像复制（存在才复制，幂等）
    if version_id == current_version_id or (current_version_id is None and number == 1):
        copy_current_assets_to_version(project_dir, target_dir)
    return version_id


def _write_current_pointer(project_dir: Path, current_version_id: str | None) -> None:
    """写入 current_version_id.txt 与 current.json（根目录兼容指针）。"""
    _write_text(project_dir / "current_version_id.txt", current_version_id or "")
    _write_json(
        project_dir / "current.json",
        {
            "schema_version": SCHEMA_VERSION,
            "current_version_id": current_version_id,
            "updated_at": _now_iso(),
        },
    )


def ensure_version_layout(project_dir: Path | str) -> dict:
    """确保项目使用目录式版本布局；可重复执行，多次调用不破坏数据。

    迁移策略：
    1. 旧 versions/vN.json 快照 → versions/vN/{version_metadata,music_spec,edit_spec,diff}.json；
    2. 旧文件保留作为兼容备份，不删除；
    3. index 升级为 schema_version=2，并写入 path/index/kind/prompt/edit_instruction；
    4. 写入 current_version_id.txt 与 current.json。
    """
    project_dir = Path(project_dir)
    versions_dir = project_dir / "versions"
    index_path = versions_dir / INDEX_FILE
    if not versions_dir.exists() or not index_path.exists():
        return {"schema_version": SCHEMA_VERSION, "current_version_id": None, "versions": []}

    index = _read_json(index_path)
    index["schema_version"] = SCHEMA_VERSION
    old_current = index.get("current_version_id")
    entries = index.get("versions", [])

    old_to_new: dict[str, str] = {}
    for i, entry in enumerate(entries):
        number = int(entry.get("version_number") or entry.get("index") or (i + 1))
        old_id = entry.get("version_id")
        new_id = _migrate_one_version(project_dir, versions_dir, number, entry, old_current)
        if old_id:
            old_to_new[old_id] = new_id
        entry["version_id"] = new_id
        entry["version_number"] = number
        entry["index"] = number
        entry["path"] = f"versions/v{number}"
        entry.setdefault("kind", "initial" if number == 1 else "edit")
        entry.setdefault("prompt", None)
        entry.setdefault("edit_instruction", entry.get("instruction"))
        entry.setdefault("instruction", entry.get("edit_instruction"))

    current = old_to_new.get(old_current) if old_current else None
    if current is None and entries:
        current = entries[0]["version_id"] if len(entries) == 1 else index.get("current_version_id")
    index["current_version_id"] = current
    _write_json(index_path, index)
    _write_current_pointer(project_dir, current)
    return index
