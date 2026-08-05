"""T30：任务存储与执行器单元测试。"""

import time

from packages.music_core.tasks.task_models import RenderTask
from packages.music_core.tasks.task_store import TaskStore
from services.api.tasks.render_task_service import RenderTaskService


def test_task_store_create_get_list():
    store = TaskStore()
    task = store.create("song-1", "midi")
    assert task.task_id
    assert task.status == "queued"
    assert store.get(task.task_id) is not None
    assert [t.task_id for t in store.list_song("song-1")] == [task.task_id]
    assert store.list_song("other") == []


def test_task_store_find_active_dedupe():
    store = TaskStore()
    task = store.create("song-1", "audio")
    assert store.find_active("song-1", "audio") is not None
    store.update(task.task_id, status="succeeded")
    assert store.find_active("song-1", "audio") is None


def test_task_store_update_fields():
    store = TaskStore()
    task = store.create("song-1", "midi")
    store.update(task.task_id, status="running", progress=50, message="工作中")
    updated = store.get(task.task_id)
    assert updated is not None
    assert updated.status == "running"
    assert updated.progress == 50
    assert updated.message == "工作中"
    assert updated.updated_at >= updated.created_at


def test_service_runs_job_to_success():
    service = RenderTaskService(max_workers=1)

    def job(task_id, report):
        report(30, "步骤一")
        report(70, "步骤二")
        return {"ok": True}

    task = service.submit("song-1", "midi", job)
    assert task.status in ("queued", "running", "succeeded")
    deadline = time.time() + 10
    while time.time() < deadline:
        current = service.get(task.task_id)
        if current is not None and current.status == "succeeded":
            break
        time.sleep(0.05)
    final = service.get(task.task_id)
    assert final is not None
    assert final.status == "succeeded"
    assert final.progress == 100
    assert final.result == {"ok": True}


def test_service_records_failure():
    service = RenderTaskService(max_workers=1)

    def job(task_id, report):
        raise RuntimeError("boom")

    task = service.submit("song-1", "audio", job)
    deadline = time.time() + 10
    while time.time() < deadline:
        current = service.get(task.task_id)
        if current is not None and current.status == "failed":
            break
        time.sleep(0.05)
    final = service.get(task.task_id)
    assert final is not None
    assert final.status == "failed"
    assert final.error == "boom"


def test_service_dedupes_active_task():
    service = RenderTaskService(max_workers=1)

    def job(task_id, report):
        time.sleep(0.3)
        return {}

    first = service.submit("song-1", "stems", job)
    second = service.submit("song-1", "stems", job)
    assert first.task_id == second.task_id
