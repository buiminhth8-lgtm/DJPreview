"""项目存储：保存 / 读取 MusicSpec、MIDI、音频、版本、混音与质量报告。"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from packages.music_core.editing.diff import diff_music_specs
from packages.music_core.mix.mix_models import MixSpec
from packages.music_core.versioning.version_assets import copy_current_assets_to_version
from packages.music_core.versioning.version_migration import ensure_version_layout
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
VERSION_METADATA_FILENAME = "version_metadata.json"
CURRENT_VERSION_ID_FILENAME = "current_version_id.txt"
CURRENT_JSON_FILENAME = "current.json"
VERSION_SCHEMA_VERSION = 2
EDIT_SPEC_FILENAME = "edit_spec.json"
DIFF_FILENAME = "diff.json"

MIX_FILENAME = "mix_spec.json"
QUALITY_FILENAME = "quality_report.json"
OPTIMIZE_FILENAME = "optimize_report.json"


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
    _write_spec_file(project_dir, music_spec)
    # T12：新项目立即初始化目录式版本结构（v1）
    init_version_if_needed(song_id, music_spec)
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
    _sync_current_version_assets(song_id)
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
    _sync_current_version_assets(song_id)


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
    """旧结构兼容路径：versions/vN.json（迁移时读取）。"""
    return _versions_dir(song_id) / f"v{version_number}.json"


def _write_version_snapshot(song_id: str, version_number: int, snapshot: dict) -> None:
    """旧结构写入（保留给迁移/兼容使用）。"""
    path = _version_snapshot_path(song_id, version_number)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_version_layout(song_id: str) -> None:
    """懒迁移：确保项目使用目录式版本布局（幂等）。"""
    ensure_version_layout(_project_dir(song_id))


def _version_dir(song_id: str, version_number: int) -> Path:
    return _versions_dir(song_id) / f"v{version_number}"


def _write_current_pointer(song_id: str, current_version_id: str | None) -> None:
    """写入根目录 current_version_id.txt 与 current.json（当前版本兼容指针）。"""
    project_dir = _project_dir(song_id)
    (project_dir / CURRENT_VERSION_ID_FILENAME).write_text(current_version_id or "", encoding="utf-8")
    (project_dir / CURRENT_JSON_FILENAME).write_text(
        json.dumps(
            {
                "schema_version": VERSION_SCHEMA_VERSION,
                "current_version_id": current_version_id,
                "updated_at": _now_iso(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_version_dir(
    song_id: str,
    version_number: int,
    version: dict,
    music_spec: MusicSpec,
    edit_spec: dict | None,
    diff: list[dict] | None,
) -> None:
    """写入目录式版本：version_metadata.json / music_spec.json / edit_spec.json / diff.json。"""
    version_dir = _version_dir(song_id, version_number)
    version_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "version_id": version["version_id"],
        "index": version_number,
        "parent_version_id": version.get("parent_version_id"),
        "created_at": version.get("created_at") or _now_iso(),
        "kind": version.get("kind", "edit"),
        "prompt": version.get("prompt"),
        "edit_instruction": version.get("edit_instruction") or version.get("instruction"),
        "notes": version.get("notes"),
        "path": f"{VERSIONS_DIR_NAME}/v{version_number}",
    }
    (version_dir / VERSION_METADATA_FILENAME).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (version_dir / "music_spec.json").write_text(
        json.dumps(music_spec.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if edit_spec is not None:
        (version_dir / EDIT_SPEC_FILENAME).write_text(
            json.dumps(edit_spec, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if diff is not None:
        (version_dir / DIFF_FILENAME).write_text(
            json.dumps(diff, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    copy_current_assets_to_version(_project_dir(song_id), version_dir)


def _read_version_dir(song_id: str, entry: dict, version_dir: Path) -> dict:
    """读取目录式版本并组装统一快照 dict（兼容旧字段）。"""
    metadata_path = version_dir / VERSION_METADATA_FILENAME
    if not metadata_path.exists():
        raise FileNotFoundError(f"版本目录缺少 version_metadata.json：{version_dir}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    number = int(entry.get("version_number") or metadata.get("index"))
    music_spec_path = version_dir / "music_spec.json"
    if not music_spec_path.exists():
        raise FileNotFoundError(f"版本目录缺少 music_spec.json：{version_dir}")
    edit_spec_path = version_dir / EDIT_SPEC_FILENAME
    diff_path = version_dir / DIFF_FILENAME
    return {
        "version_id": metadata.get("version_id") or entry.get("version_id"),
        "version_number": number,
        "index": metadata.get("index", number),
        "created_at": metadata.get("created_at"),
        "instruction": metadata.get("edit_instruction") or entry.get("instruction"),
        "edit_instruction": metadata.get("edit_instruction"),
        "parent_version_id": metadata.get("parent_version_id"),
        "kind": metadata.get("kind"),
        "prompt": metadata.get("prompt"),
        "notes": metadata.get("notes"),
        "path": metadata.get("path") or entry.get("path"),
        "edit_spec": (
            json.loads(edit_spec_path.read_text(encoding="utf-8")) if edit_spec_path.exists() else None
        ),
        "music_spec": json.loads(music_spec_path.read_text(encoding="utf-8")),
        "diff": json.loads(diff_path.read_text(encoding="utf-8")) if diff_path.exists() else None,
    }


def _sync_current_version_assets(song_id: str) -> None:
    """把根目录当前版本镜像资产同步到当前版本目录。"""
    current = get_current_version(song_id)
    if not current:
        return
    version_dir = _version_dir(song_id, int(current["version_number"]))
    copy_current_assets_to_version(_project_dir(song_id), version_dir)


def init_version_if_needed(song_id: str, music_spec: MusicSpec | None = None) -> dict:
    """旧项目自动初始化 v1（目录式）；已初始化则迁移/返回索引。"""
    index = _read_versions_index(song_id)
    if index.get("versions"):
        _ensure_version_layout(song_id)
        return index
    if music_spec is None:
        music_spec = get_project(song_id)
    version = {
        "version_id": "v1",
        "version_number": 1,
        "index": 1,
        "created_at": _now_iso(),
        "instruction": None,
        "edit_instruction": None,
        "parent_version_id": None,
        "kind": "initial",
        "prompt": music_spec.prompt,
        "notes": None,
        "path": "versions/v1",
    }
    _write_version_dir(song_id, 1, version, music_spec, edit_spec=None, diff=None)
    index = {
        "schema_version": VERSION_SCHEMA_VERSION,
        "current_version_id": version["version_id"],
        "versions": [version],
    }
    _write_versions_index(song_id, index)
    _write_current_pointer(song_id, version["version_id"])
    return index


def create_version(song_id: str, music_spec: MusicSpec, instruction: str, edit_spec: dict | None) -> dict:
    """创建目录式新版本 vN 并设为当前版本，同时同步根目录 music_spec.json。"""
    index = init_version_if_needed(song_id)
    version_number = max((v["version_number"] for v in index["versions"]), default=0) + 1
    version = {
        "version_id": f"v{version_number}",
        "version_number": version_number,
        "index": version_number,
        "created_at": _now_iso(),
        "instruction": instruction,
        "edit_instruction": instruction,
        "parent_version_id": index["current_version_id"],
        "kind": "edit",
        "prompt": music_spec.prompt,
        "notes": None,
        "path": f"versions/v{version_number}",
    }
    diff = None
    if version["parent_version_id"]:
        try:
            parent_snapshot = get_version(song_id, version["parent_version_id"])
            parent_spec = MusicSpec.model_validate(parent_snapshot["music_spec"])
            diff = diff_music_specs(parent_spec, music_spec)
        except (FileNotFoundError, KeyError, ValueError):
            diff = None
    _write_version_dir(song_id, version_number, version, music_spec, edit_spec=edit_spec, diff=diff)
    index["versions"].append(version)
    index["current_version_id"] = version["version_id"]
    index["schema_version"] = VERSION_SCHEMA_VERSION
    _write_versions_index(song_id, index)
    _write_current_pointer(song_id, version["version_id"])
    _write_spec_file(_project_dir(song_id), music_spec)
    return version


def list_versions(song_id: str) -> list[dict]:
    """返回版本列表（按版本号升序）。"""
    index = init_version_if_needed(song_id)
    return sorted(index["versions"], key=lambda v: v["version_number"])


def get_version(song_id: str, version_id: str) -> dict:
    """按 version_id 读取版本（目录式优先，旧 vN.json 兼容）。不存在抛 FileNotFoundError。"""
    index = init_version_if_needed(song_id)
    for version in index["versions"]:
        if version["version_id"] == version_id:
            number = int(version["version_number"] or version.get("index"))
            version_dir = _version_dir(song_id, number)
            if (version_dir / VERSION_METADATA_FILENAME).exists():
                return _read_version_dir(song_id, version, version_dir)
            # 兼容旧 vN.json 快照
            legacy = _version_snapshot_path(song_id, number)
            if legacy.exists():
                snapshot = json.loads(legacy.read_text(encoding="utf-8"))
                snapshot.setdefault("version_number", number)
                snapshot.setdefault("index", number)
                return snapshot
    raise FileNotFoundError(f"版本不存在：{version_id}")


def get_version_detail(song_id: str, version_id: str) -> dict:
    """读取版本详情：metadata / music_spec / edit_spec / diff（相对父版本） / is_current。

    兼容旧结构 versions/vN.json：缺失字段返回 None，不崩溃。
    """
    snapshot = get_version(song_id, version_id)
    music_spec = MusicSpec.model_validate(snapshot["music_spec"])
    edit_spec = snapshot.get("edit_spec")
    parent_version_id = snapshot.get("parent_version_id")

    diff = None
    if parent_version_id:
        try:
            parent_snapshot = get_version(song_id, parent_version_id)
            parent_spec = MusicSpec.model_validate(parent_snapshot["music_spec"])
            diff = diff_music_specs(parent_spec, music_spec)
        except FileNotFoundError:
            diff = None

    current = get_current_version(song_id)
    metadata = {
        "version_id": snapshot["version_id"],
        "index": snapshot["version_number"],
        "parent_version_id": parent_version_id,
        "created_at": snapshot.get("created_at"),
        "prompt": None,  # 旧结构未单独保存 prompt
        "edit_instruction": snapshot.get("instruction"),
        "notes": snapshot.get("notes"),
    }
    return {
        "song_id": song_id,
        "version_id": snapshot["version_id"],
        "is_current": bool(current and current["version_id"] == version_id),
        "metadata": metadata,
        "music_spec": music_spec,
        "edit_spec": edit_spec,
        "diff": diff,
    }


def get_version_diff(song_id: str, version_id: str) -> dict:
    """读取指定版本相对父版本的 diff。

    优先级：
    1. 版本快照中已保存的 diff；
    2. 否则由父版本与当前版本 MusicSpec 现场计算；
    3. 父版本缺失时返回 None + warning，不崩溃。
    """
    snapshot = get_version(song_id, version_id)
    parent_version_id = snapshot.get("parent_version_id")
    current = get_current_version(song_id)
    diff = snapshot.get("diff")
    warnings: list[str] = []

    if diff is None and parent_version_id:
        try:
            parent_snapshot = get_version(song_id, parent_version_id)
            parent_spec = MusicSpec.model_validate(parent_snapshot["music_spec"])
            target_spec = MusicSpec.model_validate(snapshot["music_spec"])
            diff = diff_music_specs(parent_spec, target_spec)
        except FileNotFoundError:
            diff = None
            warnings.append("Parent version not found; diff could not be recomputed.")

    metadata = {
        "version_id": snapshot["version_id"],
        "index": snapshot["version_number"],
        "parent_version_id": parent_version_id,
        "created_at": snapshot.get("created_at"),
        "edit_instruction": snapshot.get("instruction"),
        "prompt": None,
        "notes": snapshot.get("notes"),
    }
    return {
        "song_id": song_id,
        "version_id": snapshot["version_id"],
        "parent_version_id": parent_version_id,
        "is_current": bool(current and current["version_id"] == version_id),
        "diff": diff,
        "metadata": metadata,
        "warnings": warnings,
    }


def get_current_version(song_id: str) -> dict | None:
    """返回当前版本信息；未初始化返回 None。"""
    if (_versions_dir(song_id) / VERSIONS_INDEX_FILE).exists():
        _ensure_version_layout(song_id)
    index = _read_versions_index(song_id)
    current_id = index.get("current_version_id")
    if not current_id:
        return None
    for version in index.get("versions", []):
        if version["version_id"] == current_id:
            return version
    return None


def restore_version(song_id: str, version_id: str) -> MusicSpec:
    """恢复指定版本：设为当前版本并同步根目录 music_spec.json。

    注意：T12 只恢复 MusicSpec 与版本指针；MIDI / WAV / Mix / Stems 等
    历史资产的完整恢复将在 T13 完成。
    """
    snapshot = get_version(song_id, version_id)
    music_spec = MusicSpec.model_validate(snapshot["music_spec"])
    index = _read_versions_index(song_id)
    index["current_version_id"] = version_id
    _write_versions_index(song_id, index)
    _write_current_pointer(song_id, version_id)
    _write_spec_file(_project_dir(song_id), music_spec)
    return music_spec


# ---------- 第五阶段：混音 / 质量 / stems 存储 ----------

def _artifact_dir(song_id: str, version_id: str | None = None) -> Path:
    """版本感知的资源目录：versions/{version_id} 或当前版本目录；未启用版本则项目根。"""
    if (_versions_dir(song_id) / VERSIONS_INDEX_FILE).exists():
        _ensure_version_layout(song_id)
    project_dir = _project_dir(song_id)
    if version_id:
        return project_dir / VERSIONS_DIR_NAME / version_id
    current = get_current_version(song_id)
    if current:
        return project_dir / VERSIONS_DIR_NAME / current["version_id"]
    return project_dir


def _write_artifact_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_mix_spec_path(song_id: str, version_id: str | None = None) -> Path:
    return _artifact_dir(song_id, version_id) / MIX_FILENAME


def save_mix_spec(song_id: str, mix_spec: MixSpec, version_id: str | None = None) -> None:
    """保存 mix_spec.json 到版本目录，并同步一份到项目根目录。"""
    data = mix_spec.model_dump(mode="json")
    _write_artifact_json(get_mix_spec_path(song_id, version_id), data)
    _write_artifact_json(_project_dir(song_id) / MIX_FILENAME, data)


def get_mix_spec(song_id: str, version_id: str | None = None) -> MixSpec | None:
    path = get_mix_spec_path(song_id, version_id)
    if not path.exists():
        return None
    return MixSpec.model_validate(json.loads(path.read_text(encoding="utf-8")))


def get_quality_report_path(song_id: str, version_id: str | None = None) -> Path:
    return _artifact_dir(song_id, version_id) / QUALITY_FILENAME


def save_quality_report(song_id: str, report: dict, version_id: str | None = None) -> None:
    _write_artifact_json(get_quality_report_path(song_id, version_id), report)
    _write_artifact_json(_project_dir(song_id) / QUALITY_FILENAME, report)


def get_quality_report(song_id: str, version_id: str | None = None) -> dict | None:
    path = get_quality_report_path(song_id, version_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def get_optimize_report_path(song_id: str, version_id: str | None = None) -> Path:
    return _artifact_dir(song_id, version_id) / OPTIMIZE_FILENAME


def save_optimize_report(song_id: str, report: dict, version_id: str | None = None) -> None:
    _write_artifact_json(get_optimize_report_path(song_id, version_id), report)
    _write_artifact_json(_project_dir(song_id) / OPTIMIZE_FILENAME, report)


def get_stems_dir(song_id: str, version_id: str | None = None) -> Path:
    return _artifact_dir(song_id, version_id) / "stems"


def get_stems_zip_path(song_id: str, version_id: str | None = None) -> Path:
    return get_stems_dir(song_id, version_id) / "stems.zip"
