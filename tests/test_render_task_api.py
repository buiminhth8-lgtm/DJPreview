"""T30：异步渲染任务 API 测试（MockProvider + fallback renderer）。"""

import time

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def _create_song() -> str:
    resp = client.post("/api/v1/songs/generate", json={"prompt": "异步任务测试"})
    assert resp.status_code == 200
    return resp.json()["song_id"]


def _wait_terminal(task_id: str, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = client.get(f"/api/v1/tasks/{task_id}").json()
        if task["status"] in ("succeeded", "failed", "cancelled"):
            return task
        time.sleep(0.1)
    raise AssertionError(f"任务未在 {timeout}s 内结束：{task_id}")


def test_create_and_poll_midi_task():
    song_id = _create_song()
    resp = client.post(f"/api/v1/songs/{song_id}/tasks/render-midi")
    assert resp.status_code == 202
    task = resp.json()
    assert task["task_id"]
    assert task["song_id"] == song_id
    assert task["task_type"] == "midi"
    assert task["status"] in ("queued", "running", "succeeded")
    assert 0 <= task["progress"] <= 100

    final = _wait_terminal(task["task_id"])
    assert final["status"] == "succeeded"
    assert final["progress"] == 100
    assert "download_url" in final["result"]


def test_create_and_poll_audio_task():
    song_id = _create_song()
    resp = client.post(f"/api/v1/songs/{song_id}/tasks/render-audio")
    assert resp.status_code == 202
    task = resp.json()
    final = _wait_terminal(task["task_id"])
    assert final["status"] == "succeeded"
    assert final["progress"] == 100
    assert final["result"]["assets"]["has_audio"] is True
    assert final["result"]["audio_metadata"]["renderer"] == "fallback"


def test_create_and_poll_stems_task():
    song_id = _create_song()
    resp = client.post(f"/api/v1/songs/{song_id}/tasks/export-stems")
    assert resp.status_code == 202
    task = resp.json()
    final = _wait_terminal(task["task_id"], timeout=60)
    assert final["status"] == "succeeded"
    assert final["result"]["tracks"] >= 1
    assert final["result"]["zip_download_url"]


def test_get_missing_task_404():
    resp = client.get("/api/v1/tasks/not-exist")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "TASK_NOT_FOUND"


def test_list_song_tasks():
    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/tasks/render-midi")
    resp = client.get(f"/api/v1/songs/{song_id}/tasks")
    assert resp.status_code == 200
    tasks = resp.json()
    assert isinstance(tasks, list)
    assert any(t["task_type"] == "midi" for t in tasks)


def test_delete_task_cancels():
    song_id = _create_song()
    created = client.post(f"/api/v1/songs/{song_id}/tasks/render-midi").json()
    resp = client.delete(f"/api/v1/tasks/{created['task_id']}")
    assert resp.status_code == 200
    task = resp.json()
    assert task["task_id"] == created["task_id"]
    assert task["cancel_requested"] is True
    final = _wait_terminal(created["task_id"])
    assert final["status"] == "cancelled"


def test_delete_missing_task_404():
    resp = client.delete("/api/v1/tasks/not-exist")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "TASK_NOT_FOUND"


def test_old_sync_endpoints_still_work():
    song_id = _create_song()
    assert client.post(f"/api/v1/songs/{song_id}/midi/generate").status_code == 200
    assert client.post(f"/api/v1/songs/{song_id}/audio/render").status_code == 200
