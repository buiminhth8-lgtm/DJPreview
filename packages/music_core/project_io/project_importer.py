"""工程导入：.aimusic.zip → 新的项目目录。"""

from __future__ import annotations

import json
import uuid
import zipfile
from pathlib import Path

from services.api.schemas.music_spec import MusicSpec


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
            path = Path(name)
            # zip slip 防护
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"非法路径：{name}")
            out = (target_root / name).resolve()
            if not str(out).startswith(str(target_root) + "\\") and out != target_root:
                raise ValueError(f"路径越界：{name}")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(zf.read(name))

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
