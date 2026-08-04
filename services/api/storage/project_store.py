"""项目存储：保存 / 读取 MusicSpec JSON、MIDI、音频与版本历史。"""

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

AUDIO_FILENAME = "output.wav"
AUDIO_METADATA_FILENAME = "audio_metadata.json"
AUDIO_GENERATOR_VERSION = "stage-3-audio-v0.1"

VERSIONS_DIR_NAME = "versions"
VERSIONS_INDEX_FILE = "index.json"


def is_valid_song_id(song_id: str) -> bool:
    """校验 song_id 是否为合法 UUID 格式（防止 path traversal）。"""
    return bool(_UUID_RE.match(song_id))


def _project_dir(song_id: str) -> Path:
    """解析项目目录。song_id 必须是 UUID，防止 path traversal。"""
    if not is_valid_song_id(song_id):
        raise ValueError("非法 song_id：必须为 UUID 格式")
    return get_settings().projects_dir / song_id


def get_project_dir(song_id: str) -> Path:
    """返回项目目录（校验 UUID）。"""
    return _project_dir(song_id)


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


def _write_spec_file(project_dir: Path, music_spec: MusicSpec) -> None:
    """把 MusicSpec 写为 music_spec.json（UTF-8，中文不转义）。"""
    payload = json.dumps(
        music_spec.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    )
    (project_dir / "music_spec.json").write_text(payload, encoding="utf-8")


def save_midi_file(song_id: str, midi_data: bytes | str | Path) -> str:
    """保存 MIDI 文件到 data/projects/{song_id}/output.mid，并写入 metadata.json。"""
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


def get_wav_path(song_id: str) -> Path:
    """返回 output.wav 路径；不存在时抛出 FileNotFoundError。"""
    wav_path = _project_dir(song_id) / AUDIO_FILENAME
    if not wav_path.exists():
        raise FileNotFoundError(f"项目 {song_id} 尚未渲染音频")
    return wav_path


def project_has_wav(song_id: str) -> bool:
    """检查项目是否已渲染音频。"""
    return _project_dir(song_id).joinpath(AUDIO_FILENAME).exists()


def save_audio_metadata(song_id: str, metadata: dict) -> None:
    """保存 audio_metadata.json（UTF-8，中文不转义）。"""
    project_dir = _project_dir(song_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / AUDIO_METADATA_FILENAME).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_audio_metadata(song_id: str) -> dict | None:
    """读取 audio_metadata.json；不存在返回 None。"""
    path = _project_dir(song_id) / AUDIO_METADATA_FILENAME
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# ---------- 版本管理（第四阶段） ----------

def _versions_dir(song_id: str) -> Path:
    return _project_dir(song_id) / VERSIONS_DIR_NAME


def _read_versions_index(song_id: str) -> dict:
    path = _versions_dir(song_id) / VERSIONS_INDEX_FILE
    if not path.exists():
        return {"current_version_id": None, "versions": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_versions_index(song_id: str, index: dict) -> None:
    path = _versions_dir(song_id) / VERSIONS_INDEX_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _version_snapshot_path(song_id: str, version_number: int) -> Path:
    return _versions_dir(song_id) / f"v{version_number}.json"


def _write_version_snapshot(song_id: str, version_number: int, snapshot: dict) -> None:
    path = _version_snapshot_path(song_id, version_number)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_version_if_needed(song_id: str, music_spec: MusicSpec | None = None) -> dict:
    """旧项目自动初始化 v1；已初始化则直接返回索引。"""
    index = _read_versions_index(song_id)
    if index.get("versions"):
        return index
    if music_spec is None:
        music_spec = get_project(song_id)
    version = {
        "version_id": str(uuid.uuid4()),
        "version_number": 1,
        "created_at": _now_iso(),
        "instruction": None,
        "parent_version_id": None,
    }
    snapshot = {
        **version,
        "edit_spec": None,
        "music_spec": music_spec.model_dump(mode="json"),
    }
    _write_version_snapshot(song_id, version["version_number"], snapshot)
    index = {"current_version_id": version["version_id"], "versions": [version]}
    _write_versions_index(song_id, index)
    return index


def create_version(song_id: str, music_spec: MusicSpec, instruction: str, edit_spec: dict | None) -> dict:
    """创建新版本并设为当前版本，同时把 music_spec.json 同步为当前快照。"""
    index = init_version_if_needed(song_id)
    version_number = max((v["version_number"] for v in index["versions"]), default=0) + 1
    version = {
        "version_id": str(uuid.uuid4()),
        "version_number": version_number,
        "created_at": _now_iso(),
        "instruction": instruction,
        "parent_version_id": index["current_version_id"],
    }
    snapshot = {
        **version,
        "edit_spec": edit_spec,
        "music_spec": music_spec.model_dump(mode="json"),
    }
    _write_version_snapshot(song_id, version_number, snapshot)
    index["versions"].append(version)
    index["current_version_id"] = version["version_id"]
    _write_versions_index(song_id, index)
    _write_spec_file(_project_dir(song_id), music_spec)
    return version


def list_versions(song_id: str) -> list[dict]:
    """返回版本列表（按版本号升序）。"""
    index = init_version_if_needed(song_id)
    return sorted(index["versions"], key=lambda v: v["version_number"])


def get_version(song_id: str, version_id: str) -> dict:
    """按 version_id 读取版本快照；不存在抛出 FileNotFoundError。"""
    index = init_version_if_needed(song_id)
    for version in index["versions"]:
        if version["version_id"] == version_id:
            snapshot = json.loads(
                _version_snapshot_path(song_id, version["version_number"]).read_text(encoding="utf-8")
            )
            return snapshot
    raise FileNotFoundError(f"版本不存在：{version_id}")


def get_current_version(song_id: str) -> dict | None:
    """返回当前版本信息；未初始化返回 None。"""
    index = _read_versions_index(song_id)
    current_id = index.get("current_version_id")
    if not current_id:
        return None
    for version in index.get("versions", []):
        if version["version_id"] == current_id:
            return version
    return None


def restore_version(song_id: str, version_id: str) -> MusicSpec:
    """恢复指定版本：设为当前版本并同步根目录 music_spec.json。"""
    snapshot = get_version(song_id, version_id)
    music_spec = MusicSpec.model_validate(snapshot["music_spec"])
    index = _read_versions_index(song_id)
    index["current_version_id"] = version_id
    _write_versions_index(song_id, index)
    _write_spec_file(_project_dir(song_id), music_spec)
    return music_spec
