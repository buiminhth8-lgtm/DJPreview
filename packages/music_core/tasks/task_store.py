"""任务存储：内存 + 轻量 JSON 持久化（线程安全）。

持久化到 data/tasks/render_tasks.json；服务重启后重新加载，
重启前 queued/running 的任务标记为 failed（线程已丢失）。
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from packages.music_core.tasks.task_models import RenderTask

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskStore:
    def __init__(self, persist_path: Path | str | None = None) -> None:
        self._tasks: dict[str, RenderTask] = {}
        self._lock = threading.RLock()
        self.persist_path = Path(persist_path) if persist_path is not None else None
        self._load()

    def _load(self) -> None:
        if self.persist_path is None or not self.persist_path.exists():
            return
        try:
            data = json.loads(self.persist_path.read_text(encoding="utf-8"))
            for item in data:
                task = RenderTask.model_validate(item)
                if task.status in ("queued", "running"):
                    # 服务重启后原执行线程已丢失
                    task.status = "failed"
                    task.error = "服务重启导致任务中断"
                    task.message = "任务中断"
                self._tasks[task.task_id] = task
        except Exception as exc:  # noqa: BLE001 - 持久化损坏不影响服务启动
            logger.warning("任务持久化文件读取失败：%s", exc)

    def _persist(self) -> None:
        if self.persist_path is None:
            return
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            payload = [
                task.model_dump(mode="json") for task in self._tasks.values()
            ]
            self.persist_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:  # noqa: BLE001 - 写日志失败不影响主流程
            logger.warning("任务持久化写入失败：%s", exc)

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
            self._persist()
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
            self._persist()
