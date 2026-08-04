"""工程导出：项目目录 → .aimusic.zip。"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

_APP_VERSION = "stage-6-v0.1"

# zip 内相对路径 → 项目内路径
_FILES = [
    "music_spec.json",
    "output.mid",
    "output.wav",
    "audio_metadata.json",
    "metadata.json",
    "mix_spec.json",
    "quality_report.json",
    "optimize_report.json",
    "stems/stems_metadata.json",
    "prompts.json",
    "eval_report.json",
    "versions/index.json",
]


def export_project_bundle(song_id: str, project_dir: Path, output_path: Path) -> Path:
    """导出 .aimusic.zip；zip 内路径稳定、不含绝对路径与敏感文件。"""
    project_dir = Path(project_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    contains: dict[str, bool] = {}
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = {
            "format": "ai-music-project",
            "format_version": "0.1",
            "song_id": song_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "app_version": _APP_VERSION,
            "contains": contains,
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        for rel in _FILES:
            src = project_dir / rel
            if src.exists():
                zf.write(src, rel)
                contains[rel] = True

        # versions 快照
        versions_dir = project_dir / "versions"
        if versions_dir.exists():
            for snapshot in sorted(versions_dir.glob("v*.json")):
                zf.write(snapshot, f"versions/{snapshot.name}")
        contains["versions"] = (versions_dir / "index.json").exists()
        contains["music_spec"] = (project_dir / "music_spec.json").exists()
        contains["midi"] = (project_dir / "output.mid").exists()
        contains["audio"] = (project_dir / "output.wav").exists()
        contains["mix"] = (project_dir / "mix_spec.json").exists()
        contains["quality_report"] = (project_dir / "quality_report.json").exists()

        # 重写 manifest（contains 已填全）
        manifest["contains"] = contains
        # zipfile 不支持覆盖，删除后重写
        # 用新 zip 重写：简单方案是收集所有条目
    return _rewrite_manifest(output_path, contains, song_id)


def _rewrite_manifest(output_path: Path, contains: dict, song_id: str) -> Path:
    """重建 zip 以写入完整 manifest（contains 填充后）。"""
    tmp = output_path.with_suffix(".tmp.zip")
    manifest = {
        "format": "ai-music-project",
        "format_version": "0.1",
        "song_id": song_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "app_version": _APP_VERSION,
        "contains": contains,
    }
    with zipfile.ZipFile(output_path, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "manifest.json":
                data = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
            zout.writestr(item.filename, data)
    tmp.replace(output_path)
    return output_path
