"""评估数据模型。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_run_id() -> str:
    return uuid.uuid4().hex[:12]


class EvalCase(BaseModel):
    id: str
    prompt: str
    style_template_id: str | None = None
    expected_traits: dict = Field(default_factory=dict)
    notes: str | None = None


class EvalResult(BaseModel):
    case_id: str
    song_id: str | None = None
    score: float
    quality_score: float
    trait_matches: dict = Field(default_factory=dict)
    music_spec: dict | None = None
    midi_path: str | None = None
    quality_report: dict | None = None

    # T15：音频渲染状态
    render_audio: bool = False
    audio_rendered: bool = False
    audio_path: str | None = None
    audio_duration_seconds: float | None = None
    renderer: str | None = None
    render_error: str | None = None

    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class EvalReport(BaseModel):
    run_id: str = Field(default_factory=_new_run_id)
    created_at: str = Field(default_factory=_utc_now_iso)
    render_audio: bool = False
    total_cases: int
    passed_cases: int
    failed_cases: int = 0
    average_score: float
    audio_rendered_cases: int = 0
    audio_failed_cases: int = 0
    results: list[EvalResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary: str
