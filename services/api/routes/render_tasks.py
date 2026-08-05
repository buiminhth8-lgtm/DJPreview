"""异步渲染任务 API（T30）：MIDI / WAV / stems。"""

from __future__ import annotations

from fastapi import APIRouter

from packages.music_core.tasks.task_models import RenderTask
from services.api.errors import invalid_request, project_not_found, task_not_found
from services.api.schemas.api_models import RenderAudioTaskRequest
from services.api.storage.project_store import get_project, save_project_soundfont
from services.api.tasks.render_task_service import (
    RenderTaskService,
    audio_render_job,
    midi_render_job,
    stems_export_job,
)

router = APIRouter()

_service = RenderTaskService()


def _require_project(song_id: str) -> None:
    try:
        get_project(song_id)
    except FileNotFoundError as exc:
        raise project_not_found(song_id) from None
    except ValueError as exc:
        raise invalid_request(str(exc)) from None


@router.post("/songs/{song_id}/tasks/render-midi", response_model=RenderTask, status_code=202, summary="异步生成 MIDI")
def start_render_midi(song_id: str) -> RenderTask:
    _require_project(song_id)
    return _service.submit(song_id, "midi", lambda task_id, report: midi_render_job(song_id, task_id, report))


@router.post("/songs/{song_id}/tasks/render-audio", response_model=RenderTask, status_code=202, summary="异步渲染 WAV")
def start_render_audio(song_id: str, req: RenderAudioTaskRequest | None = None) -> RenderTask:
    _require_project(song_id)
    if req is not None and req.soundfont_id:
        save_project_soundfont(
            song_id,
            {"soundfont_id": req.soundfont_id, "soundfont_name": None, "renderer": "auto"},
        )
    return _service.submit(song_id, "audio", lambda task_id, report: audio_render_job(song_id, task_id, report))


@router.post("/songs/{song_id}/tasks/export-stems", response_model=RenderTask, status_code=202, summary="异步导出 stems")
def start_export_stems(song_id: str) -> RenderTask:
    _require_project(song_id)
    return _service.submit(song_id, "stems", lambda task_id, report: stems_export_job(song_id, task_id, report))


@router.get("/tasks/{task_id}", response_model=RenderTask, summary="查询任务状态")
def get_render_task(task_id: str) -> RenderTask:
    task = _service.get(task_id)
    if task is None:
        raise task_not_found(task_id)
    return task


@router.delete("/tasks/{task_id}", response_model=RenderTask, summary="取消任务")
def cancel_render_task(task_id: str) -> RenderTask:
    task = _service.cancel(task_id)
    if task is None:
        raise task_not_found(task_id)
    return task


@router.get("/songs/{song_id}/tasks", response_model=list[RenderTask], summary="歌曲任务列表")
def list_render_tasks(song_id: str) -> list[RenderTask]:
    _require_project(song_id)
    return _service.list_song(song_id)
