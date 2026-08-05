"""T30+：任务执行器抽象（进程内默认 / Celery 可选）测试。"""

import os

from services.api.tasks.task_executor import (
    CeleryExecutor,
    InProcessExecutor,
    create_task_executor,
)


def test_default_backend_is_inprocess(monkeypatch):
    monkeypatch.delenv("TASK_BACKEND", raising=False)
    executor = create_task_executor(max_workers=1)
    assert isinstance(executor, InProcessExecutor)


def test_celery_backend_selected_by_env(monkeypatch):
    monkeypatch.setenv("TASK_BACKEND", "celery")
    executor = create_task_executor()
    assert isinstance(executor, CeleryExecutor)


def test_celery_executor_requires_celery_package():
    """未安装 celery 时给出清晰错误，而不是静默降级。"""
    executor = CeleryExecutor()
    try:
        import celery  # noqa: F401
    except ImportError:
        try:
            executor._ensure_app()
        except RuntimeError as exc:
            assert "TASK_BACKEND=celery" in str(exc)
        else:
            raise AssertionError("缺少 celery 时应抛 RuntimeError")
