"""项目存储：保存 / 读取 MusicSpec JSON。"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from services.api.dependencies.config import get_settings
from services.api.schemas.music_spec import MusicSpec

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _project_dir(song_id: str) -> Path:
    """解析项目目录。song_id 必须是 UUID，防止 path traversal。"""
    if not _UUID_RE.match(song_id):
        raise ValueError("非法 song_id：必须为 UUID 格式")
    return get_settings().projects_dir / song_id


def create_project(music_spec: MusicSpec) -> str:
    """创建项目并保存 music_spec.json，返回 song_id。"""
    song_id = str(uuid.uuid4())
    project_dir = _project_dir(song_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    spec_path = project_dir / "music_spec.json"
    payload = json.dumps(
        music_spec.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    )
    spec_path.write_text(payload, encoding="utf-8")
    return song_id


def get_project(song_id: str) -> MusicSpec:
    """按 song_id 读取项目。不存在时抛出 FileNotFoundError。"""
    project_dir = _project_dir(song_id)
    spec_path = project_dir / "music_spec.json"
    if not spec_path.exists():
        raise FileNotFoundError(f"项目不存在：{song_id}")
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    return MusicSpec.model_validate(data)
