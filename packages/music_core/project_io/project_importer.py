"""工程导入：.aimusic.zip → 新的项目目录。"""

from __future__ import annotations

import json
import uuid
import zipfile
from pathlib import Path

from services.api.schemas.music_spec import MusicSpec


def _safe_extract_target(projects_root: Path, new_song_id: str, name: str) -> Path:
    """校验 zip 内路径并返回安全的解压目标（防 zip slip，跨平台兼容）。"""
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


def import_project_bundle(bundle_path: Path, projects_root: Path) -> dict:
    """导入 .aimusic.zip 到新的 song_id 目录（防 zip slip）。"""
    projects_root = Path(projects_root)
    projects_root.mkdir(parents=True, exist_ok=True)
    new_song_id = str(uuid.uuid4())
    target_root = (projects_root / new_song_id).resolve()

    try:
        zf = zipfile.ZipFile(bundle_path, "r")
    except zipfile.BadZipFile as exc:
        raise ValueError("不是有效的 zip 文件") from exc
    with zf:
        names = zf.namelist()
        if "manifest.json" not in names:
            raise ValueError("缺少 manifest.json，不是有效的 .aimusic.zip")
        manifest = json.loads(zf.read("manifest.json"))
        if manifest.get("format") != "ai-music-project":
            raise ValueError(f"不支持的工程格式：{manifest.get('format')}")

        for name in names:
            if name.endswith("/"):
                # 目录项：仅创建目录，不写入文件
                _safe_extract_target(projects_root, new_song_id, name).mkdir(parents=True, exist_ok=True)
                continue
            target = _safe_extract_target(projects_root, new_song_id, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(name))

    spec_path = target_root / "music_spec.json"
    if not spec_path.exists():
        raise ValueError("缺少 music_spec.json")
    spec = MusicSpec.model_validate(json.loads(spec_path.read_text(encoding="utf-8")))

    summary = {
        "tracks": len(spec.tracks),
        "bars": spec.length.bars,
        "files": len(names),
        "has_versions": (target_root / "versions" / "index.json").exists(),
        "has_midi": (target_root / "output.mid").exists(),
        "has_audio": (target_root / "output.wav").exists(),
    }
    return {"song_id": new_song_id, "imported": True, "summary": summary}
