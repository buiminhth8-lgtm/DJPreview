"""Evaluation Runner 测试。"""

from packages.music_core.evaluation.eval_fixtures import get_eval_cases
from packages.music_core.evaluation.eval_models import EvalReport
from packages.music_core.evaluation.eval_runner import run_generation_eval


def test_builtin_cases_at_least_8():
    assert len(get_eval_cases()) >= 8


def test_run_generation_eval_returns_report():
    report = run_generation_eval(get_eval_cases()[:3])
    assert isinstance(report, EvalReport)
    assert report.total_cases == 3
    assert report.results
    assert 0 <= report.average_score <= 100


def test_each_result_has_warnings_errors():
    report = run_generation_eval(get_eval_cases()[:2])
    for result in report.results:
        assert isinstance(result.warnings, list)
        assert isinstance(result.errors, list)


def test_no_external_llm_dependency():
    # 使用 MockProvider，不依赖 DeepSeek
    report = run_generation_eval(get_eval_cases()[:1])
    assert not any(r.errors for r in report.results)
