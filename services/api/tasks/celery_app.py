"""Celery 应用与 worker 任务（生产可选后端）。

部署方式（需要 Redis）：
  pip install -r requirements-celery.txt
  export TASK_BACKEND=celery
  export CELERY_BROKER_URL=redis://localhost:6379/0
  celery -A services.api.tasks.celery_app worker --loglevel=info
"""

from __future__ import annotations

import os

from packages.music_core.tasks.task_store import TaskStore


def _task_store() -> TaskStore:
    return TaskStore(persist_path=os.environ.get(
        "TASK_PERSIST_PATH",
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "tasks", "render_tasks.json"),
    ))


def _job_registry(task_type: str, song_id: str, task_id: str):
    """worker 侧按 task_type 装配本地 job 闭包（与 inprocess 后端共用实现）。"""
    from services.api.tasks.render_task_service import (
        audio_render_job,
        midi_render_job,
        stems_export_job,
    )

    jobs = {
        "midi": midi_render_job,
        "audio": audio_render_job,
        "stems": stems_export_job,
    }
    job = jobs.get(task_type)
    if job is None:
        raise ValueError(f"未知任务类型：{task_type}")
    return lambda task_id_, report: job(song_id, task_id_, report)


def _run_render_task(task_id: str, song_id: str, task_type: str) -> dict:
    """worker 执行体：与 InProcessExecutor._run 保持相同状态机语义。"""
    from services.api.tasks.task_executor import InProcessExecutor, TaskCancelled, song_render_lock

    store = _task_store()
    task = store.get(task_id)
    if task is None:
        raise FileNotFoundError(f"任务不存在：{task_id}")
    store.update(task_id, status="running", progress=10, message="启动任务")
    job = _job_registry(task_type, song_id, task_id)

    def report(progress: int, message: str | None = None) -> None:
        current = store.get(task_id)
        if current is not None and current.cancel_requested:
            raise TaskCancelled("任务已取消")
        store.update(task_id, progress=max(0, min(100, int(progress))), message=message)

    try:
        with song_render_lock(song_id):
            result = job(task_id, report)
        current = store.get(task_id)
        if current is not None and current.cancel_requested:
            store.update(task_id, status="cancelled", message="任务已取消")
        else:
            store.update(task_id, status="succeeded", progress=100, message="任务完成", result=result or {})
        return result or {}
    except TaskCancelled:
        store.update(task_id, status="cancelled", progress=0, message="任务已取消")
        return {}
    except Exception as exc:  # noqa: BLE001 - 单个任务失败不影响 worker
        store.update(task_id, status="failed", error=str(exc), message="任务失败")
        raise


def _make_celery_app():
    try:
        from celery import Celery
    except ImportError:  # pragma: no cover - 未安装 celery 时仅构建描述
        return None

    app = Celery(
        "ai_music_mvp",
        broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    )
    app.conf.task_serializer = "json"
    app.conf.result_serializer = "json"
    app.conf.accept_content = ["json"]
    app.conf.task_track_started = True

    @app.task(name="services.api.tasks.celery_app.run_render_task", bind=True)
    def run_render_task(self, task_id: str, song_id: str, task_type: str) -> dict:
        return _run_render_task(task_id, song_id, task_type)

    return app


celery_app = _make_celery_app()


__all__ = ["celery_app", "_run_render_task"]
