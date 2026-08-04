"""Evaluation Runner 测试。"""

from pathlib import Path

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


# ---------- T15：render_audio 语义 ----------

def test_render_audio_false_does_not_call_renderer(tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("render_audio=false 不应调用音频渲染器")

    monkeypatch.setattr("packages.music_core.evaluation.eval_runner.get_audio_renderer", boom)
    report = run_generation_eval(get_eval_cases()[:2], render_audio=False, output_dir=tmp_path)
    assert report.total_cases == 2
    for result in report.results:
        assert result.render_audio is False
        assert result.audio_rendered is False
        assert result.audio_path is None
        assert result.render_error is None
    assert report.audio_rendered_cases == 0
    assert report.audio_failed_cases == 0


def test_render_audio_true_uses_fallback_renderer(tmp_path):
    report = run_generation_eval(get_eval_cases()[:2], render_audio=True, output_dir=tmp_path)
    assert report.render_audio is True
    rendered = [r for r in report.results if r.audio_rendered]
    assert rendered
    for result in rendered:
        assert result.audio_path
        assert Path(result.audio_path).exists()
        assert result.renderer == "fallback"
        assert result.audio_duration_seconds is None or result.audio_duration_seconds > 0
        assert result.render_error is None
    assert report.audio_rendered_cases >= 1
    assert report.audio_failed_cases == 0


def test_single_case_render_failure_does_not_break_report(tmp_path, monkeypatch):
    class BoomRenderer:
        name = "boom"

        def render_wav(self, *args, **kwargs):
            raise RuntimeError("renderer exploded")

    monkeypatch.setattr(
        "packages.music_core.evaluation.eval_runner.get_audio_renderer",
        lambda: BoomRenderer(),
    )
    report = run_generation_eval(get_eval_cases()[:2], render_audio=True, output_dir=tmp_path)
    assert report.total_cases == 2
    for result in report.results:
        assert result.audio_rendered is False
        assert result.render_error
        assert any("Audio rendering failed" in w for w in result.warnings)
    assert report.audio_rendered_cases == 0
    assert report.audio_failed_cases >= 1
