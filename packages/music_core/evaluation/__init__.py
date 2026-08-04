"""批量评估模块。"""

from packages.music_core.evaluation.eval_fixtures import get_eval_cases
from packages.music_core.evaluation.eval_models import EvalCase, EvalReport, EvalResult
from packages.music_core.evaluation.eval_runner import run_generation_eval

__all__ = ["EvalCase", "EvalReport", "EvalResult", "get_eval_cases", "run_generation_eval"]
