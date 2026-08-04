"""项目存储：保存 / 读取 MusicSpec JSON 与 MIDI 文件。"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from services.api.dependencies.config import get_settings
from services.api.schemas.music_spec import MusicSpec

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

MIDI_FILENAME = "output.mid"
METADATA_FILENAME = "metadata.json"
GENERATOR_VERSION = "stage-2-midi-v0.1"


def is_valid_song_id(song_id: str) -> bool:
    """校验 song_id 是否为合法 UUID 格式（防止 path traversal）。"""
    return bool(_UUID_RE.match(song_id))


def _project_dir(song_id: str) -> Path:
    """解析项目目录。song_id 必须是 UUID，防止 path traversal。"""
    if not is_valid_song_id(song_id):
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


def save_midi_file(song_id: str, midi_data: bytes | str | Path) -> str:
    """保存 MIDI 文件到 data/projects/{song_id}/output.mid，并写入 metadata.json。

    参数可以是 bytes、文件路径字符串或 Path；返回文件名 output.mid。
    """
    project_dir = _project_dir(song_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    midi_path = project_dir / MIDI_FILENAME
    if isinstance(midi_data, bytes):
        midi_path.write_bytes(midi_data)
    else:
        src = Path(midi_data)
        midi_path.write_bytes(src.read_bytes())

    metadata = {
        "midi_file": MIDI_FILENAME,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_version": GENERATOR_VERSION,
    }
    (project_dir / METADATA_FILENAME).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return MIDI_FILENAME


def get_midi_path(song_id: str) -> Path:
    """返回 output.mid 路径；不存在时抛出 FileNotFoundError。"""
    midi_path = _project_dir(song_id) / MIDI_FILENAME
    if not midi_path.exists():
        raise FileNotFoundError(f"项目 {song_id} 尚未生成 MIDI")
    return midi_path


def project_has_midi(song_id: str) -> bool:
    """检查项目是否已生成 MIDI。"""
    return _project_dir(song_id).joinpath(MIDI_FILENAME).exists()
