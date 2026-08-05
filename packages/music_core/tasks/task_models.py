"""异步渲染任务数据模型（T30）。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TaskStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]


class RenderTask(BaseModel):
    """单个渲染任务。task_type：midi / audio / stems。"""

    task_id: str
    song_id: str
    task_type: str
    status: TaskStatus = "queued"
    progress: int = 0
    message: str | None = None
    error: str | None = None
    result: dict = Field(default_factory=dict)
    created_at: str
    updated_at: str
