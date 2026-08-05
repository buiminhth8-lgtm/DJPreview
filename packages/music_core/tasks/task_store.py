"""进程内任务存储（线程安全；服务重启后丢失，见 docs/RENDER_TASKS.md 限制说明）。"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

from packages.music_core.tasks.task_models import RenderTask


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskStore:
    def __init__(self) -> None:
        self._tasks: dict[str, RenderTask] = {}
        self._lock = threading.Lock()

    def create(self, song_id: str, task_type: str) -> RenderTask:
        task = RenderTask(
            task_id=uuid.uuid4().hex[:12],
            song_id=song_id,
            task_type=task_type,
            created_at=_now_iso(),
            updated_at=_now_iso(),
        )
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def get(self, task_id: str) -> RenderTask | None:
        with self._lock:
            return self._tasks.get(task_id)

    def list_song(self, song_id: str) -> list[RenderTask]:
        with self._lock:
            return [task for task in self._tasks.values() if task.song_id == song_id]

    def find_active(self, song_id: str, task_type: str) -> RenderTask | None:
        """同 song + 同类型仍在 queued/running 的任务（去重用）。"""
        with self._lock:
            for task in self._tasks.values():
                if (
                    task.song_id == song_id
                    and task.task_type == task_type
                    and task.status in ("queued", "running")
                ):
                    return task
        return None

    def update(self, task_id: str, **fields) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            for key, value in fields.items():
                setattr(task, key, value)
            task.updated_at = _now_iso()
