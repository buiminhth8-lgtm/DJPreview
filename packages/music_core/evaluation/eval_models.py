"""评估数据模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


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
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class EvalReport(BaseModel):
    created_at: str
    total_cases: int
    passed_cases: int
    average_score: float
    results: list[EvalResult] = Field(default_factory=list)
    summary: str
