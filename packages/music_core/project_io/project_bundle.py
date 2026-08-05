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
    """导出 .aimusic.zip；zip 内路径稳定、不含绝对路径与敏感文件。

    单遍写入：先收集 manifest 的 contains 信息，再一次性写 zip，
    避免“写 zip → 重写 manifest → replace”两步法在 Windows 上因文件占用导致 PermissionError。
    """
    project_dir = Path(project_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 先收集 contains 信息
    contains: dict[str, bool] = {}
    for rel in _FILES:
        contains[rel] = (project_dir / rel).exists()
    versions_dir = project_dir / "versions"
    contains["versions"] = (versions_dir / "index.json").exists()
    contains["music_spec"] = (project_dir / "music_spec.json").exists()
    contains["midi"] = (project_dir / "output.mid").exists()
    contains["audio"] = (project_dir / "output.wav").exists()
    contains["mix"] = (project_dir / "mix_spec.json").exists()
    contains["quality_report"] = (project_dir / "quality_report.json").exists()

    manifest = {
        "format": "ai-music-project",
        "format_version": "0.1",
        "song_id": song_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "app_version": _APP_VERSION,
        "contains": contains,
    }

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for rel in _FILES:
            src = project_dir / rel
            if src.exists():
                zf.write(src, rel)
        # versions 快照
        if versions_dir.exists():
            for snapshot in sorted(versions_dir.glob("v*.json")):
                zf.write(snapshot, f"versions/{snapshot.name}")
    return output_path
