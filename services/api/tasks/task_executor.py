"""任务执行器抽象：进程内（默认）与 Celery/Redis（生产可选）双后端。

- `TASK_BACKEND` 未设置或为 `inprocess`：使用 ThreadPoolExecutor（T30 现状，离线可用）；
- `TASK_BACKEND=celery`：把任务发布到 Celery（需单独部署 Redis + worker，见 docs/RENDER_TASKS.md）。
"""

from __future__ import annotations

import logging
import os
import threading
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from packages.music_core.tasks.task_models import RenderTask
from packages.music_core.tasks.task_store import TaskStore

logger = logging.getLogger(__name__)

ProgressReporter = Callable[[int, str | None], None]
RenderJob = Callable[[str, ProgressReporter], dict]


class TaskExecutor(ABC):
    """提交任务的抽象接口；状态仍统一写入 TaskStore（前端 API 不变）。"""

    @abstractmethod
    def submit(self, store: TaskStore, task: RenderTask, job: RenderJob) -> None:
        """异步执行 task；执行器负责在完成/失败时更新 TaskStore。"""

    @abstractmethod
    def shutdown(self) -> None:
        """优雅关闭（进程退出时调用）。"""


# ---------- 进程内执行器（默认，无需外部依赖） ----------

# 每首歌一把可重入锁：同 song 的同步 / 异步渲染串行执行，避免文件互相覆盖
_SONG_LOCKS: dict[str, threading.RLock] = {}
_SONG_LOCKS_GUARD = threading.Lock()


def song_render_lock(song_id: str) -> threading.RLock:
    """返回该歌曲的渲染锁（可重入）。"""
    with _SONG_LOCKS_GUARD:
        return _SONG_LOCKS.setdefault(song_id, threading.RLock())


class TaskCancelled(RuntimeError):
    """任务被取消。"""


class InProcessExecutor(TaskExecutor):
    """进程内 ThreadPoolExecutor；服务重启后 queued/running 任务中断（由 TaskStore 标记失败）。"""

    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="render-task")

    def submit(self, store: TaskStore, task: RenderTask, job: RenderJob) -> None:
        self._executor.submit(self._run, store, task, job)

    def _run(self, store: TaskStore, task: RenderTask, job: RenderJob) -> None:
        task_id = task.task_id
        current = store.get(task_id)
        if current is not None and current.status == "cancelled":
            return
        store.update(task_id, status="running", progress=10, message="启动任务")

        def report(progress: int, message: str | None = None) -> None:
            current = store.get(task_id)
            if current is not None and current.cancel_requested:
                raise TaskCancelled("任务已取消")
            store.update(
                task_id,
                progress=max(0, min(100, int(progress))),
                message=message,
            )

        try:
            with song_render_lock(task.song_id):
                result = job(task_id, report)
            current = store.get(task_id)
            if current is not None and current.cancel_requested:
                store.update(task_id, status="cancelled", message="任务已取消")
            else:
                store.update(
                    task_id,
                    status="succeeded",
                    progress=100,
                    message="任务完成",
                    result=result or {},
                )
        except TaskCancelled:
            store.update(task_id, status="cancelled", progress=0, message="任务已取消")
        except Exception as exc:  # noqa: BLE001 - 单个任务失败不影响服务进程
            logger.warning("渲染任务 %s 失败：%s", task_id, exc)
            store.update(task_id, status="failed", error=str(exc), message="任务失败")

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


# ---------- Celery / Redis 执行器（生产可选） ----------


class CeleryExecutor(TaskExecutor):
    """把任务发布到 Celery（需要 redis broker + celery worker，见 docs/RENDER_TASKS.md）。

    延迟导入 Celery：未安装 celery/redis 或未配置 TASK_BACKEND=celery 时不影响现有功能。
    """

    def __init__(self, broker_url: str | None = None) -> None:
        self._broker_url = broker_url or os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        self._app = None

    def _ensure_app(self):
        if self._app is not None:
            return self._app
        try:
            from services.api.tasks.celery_app import celery_app
        except ImportError as exc:  # pragma: no cover - 依赖缺失时给出清晰报错
            raise RuntimeError(
                "TASK_BACKEND=celery 需要安装 celery + redis：pip install -r requirements-celery.txt"
            ) from exc
        if celery_app is None:  # celery 未安装时 celery_app 为 None
            raise RuntimeError(
                "TASK_BACKEND=celery 需要安装 celery + redis：pip install -r requirements-celery.txt"
            )
        self._app = celery_app
        if self._broker_url:
            self._app.conf.broker_url = self._broker_url
        return self._app

    def submit(self, store: TaskStore, task: RenderTask, job: RenderJob) -> None:
        app = self._ensure_app()
        # job 为本地闭包，无法序列化；Celery 后端只传递任务元数据，
        # worker 侧按 task_type 重新装配（见 celery_app.py 的 job registry）。
        app.send_task(
            "services.api.tasks.celery_app.run_render_task",
            kwargs={"task_id": task.task_id, "song_id": task.song_id, "task_type": task.task_type},
        )

    def shutdown(self) -> None:
        return None


def create_task_executor(max_workers: int = 2) -> TaskExecutor:
    """按 TASK_BACKEND 选择执行器（默认进程内）。"""
    backend = os.environ.get("TASK_BACKEND", "inprocess").strip().lower()
    if backend == "celery":
        logger.info("使用 Celery/Redis 任务后端")
        return CeleryExecutor()
    return InProcessExecutor(max_workers=max_workers)
