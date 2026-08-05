"""异步渲染任务服务：提交 / 执行 / 查询 / 取消（执行后端可插拔）。"""

from __future__ import annotations

import logging
from pathlib import Path

from packages.music_core.tasks.task_models import RenderTask
from packages.music_core.tasks.task_store import TaskStore
from services.api.tasks.task_executor import (
    InProcessExecutor,
    ProgressReporter,
    TaskCancelled,
    TaskExecutor,
    create_task_executor,
    song_render_lock,
)

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class RenderTaskService:
    """提交 / 执行渲染任务；同 song + 同类型去重，避免文件互相覆盖。

    执行后端由 TASK_BACKEND 决定（默认进程内；celery 需 Redis + worker）。
    """

    def __init__(
        self,
        max_workers: int = 2,
        persist_path: Path | str | None = None,
        executor: TaskExecutor | None = None,
    ) -> None:
        if persist_path is None:
            persist_path = _PROJECT_ROOT / "data" / "tasks" / "render_tasks.json"
        self._store = TaskStore(persist_path=persist_path)
        self._executor = executor or create_task_executor(max_workers=max_workers)

    @property
    def store(self) -> TaskStore:
        return self._store

    def submit(self, song_id: str, task_type: str, job) -> RenderTask:
        existing = self._store.find_active(song_id, task_type)
        if existing is not None:
            return existing
        task = self._store.create(song_id, task_type)
        self._executor.submit(self._store, task, job)
        return task

    def get(self, task_id: str) -> RenderTask | None:
        return self._store.get(task_id)

    def list_song(self, song_id: str) -> list[RenderTask]:
        return self._store.list_song(song_id)

    def cancel(self, task_id: str) -> RenderTask | None:
        """取消任务：queued 立即置 cancelled；running 标记取消，在执行检查点中止。"""
        task = self._store.get(task_id)
        if task is None:
            return None
        self._store.update(task_id, cancel_requested=True)
        if task.status == "queued":
            self._store.update(task_id, status="cancelled", message="任务已取消")
        return self._store.get(task_id)


# ---------- 渲染任务实现（复用现有 composer / renderer / version store） ----------


def midi_render_job(song_id: str, task_id: str, report: ProgressReporter) -> dict:
    from services.api.routes.songs import _generate_midi_for

    report(30, "读取 MusicSpec 并编排")
    response, _path = _generate_midi_for(song_id)
    report(60, "MIDI 已写入")
    report(90, "保存资源元数据")
    report(100, "MIDI 渲染完成")
    return {
        "midi_file": response.midi_file,
        "download_url": response.download_url,
        "summary": response.summary.model_dump(mode="json"),
    }


def audio_render_job(song_id: str, task_id: str, report: ProgressReporter) -> dict:
    from services.api.routes.songs import _assets_response, _ensure_midi_for, _render_audio_for

    report(20, "确保 MIDI 存在")
    _ensure_midi_for(song_id)
    report(50, "开始渲染 WAV")
    response = _render_audio_for(song_id)
    report(85, "WAV 已渲染，写入元数据")
    assets = _assets_response(song_id)
    report(100, "音频渲染完成")
    return {
        "assets": assets.model_dump(mode="json"),
        "audio_metadata": response.metadata.model_dump(mode="json"),
    }


def stems_export_job(song_id: str, task_id: str, report: ProgressReporter) -> dict:
    from packages.music_core.versioning.version_assets import mirror_stems_to_root
    from services.api.dependencies.config import get_settings
    from services.api.routes.songs import (
        _load_or_create_mix,
        export_stems_impl,
        get_project_dir,
        get_stems_dir,
    )
    from services.api.storage.project_store import get_project

    report(20, "读取 MusicSpec 与混音")
    spec = get_project(song_id)
    mix, version_id = _load_or_create_mix(song_id)
    settings = get_settings()
    stems_dir = get_stems_dir(song_id, version_id)
    report(50, "拆分并渲染分轨")
    result = export_stems_impl(
        song_id,
        spec,
        mix,
        stems_dir,
        sample_rate=settings.audio_sample_rate,
        gain=settings.audio_gain,
    )
    mirror_stems_to_root(stems_dir, get_project_dir(song_id) / "stems")
    report(90, "打包 stems.zip")
    report(100, "stems 导出完成")
    return {
        "tracks": len(result.tracks),
        "zip_download_url": f"/api/v1/songs/{song_id}/stems/download",
        "warnings": result.warnings,
    }
