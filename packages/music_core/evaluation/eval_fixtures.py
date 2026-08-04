"""内置评估用例。"""

from __future__ import annotations

from packages.music_core.evaluation.eval_models import EvalCase

_CASES: list[EvalCase] = [
    EvalCase(
        id="cinematic_piano",
        prompt="生成一段忧郁空灵的钢琴配乐",
        style_template_id="cinematic_piano",
        expected_traits={"mode": "minor", "has_track_role": "pad", "min_quality_score": 50},
        notes="忧郁电影钢琴",
    ),
    EvalCase(
        id="happy_pop",
        prompt="一首欢快明亮的流行歌",
        style_template_id="pop_ballad",
        expected_traits={"tempo_range": [80, 130], "has_track_role": "drums", "min_quality_score": 50},
        notes="欢快流行",
    ),
    EvalCase(
        id="chinese_cinematic",
        prompt="带有中国风韵味的电影配乐",
        style_template_id="chinese_cinematic",
        expected_traits={"mode": "pentatonic", "has_track_role": "pad", "min_quality_score": 50},
        notes="中国风配乐",
    ),
    EvalCase(
        id="game_battle",
        prompt="紧张激烈的游戏战斗音乐",
        style_template_id="game_battle",
        expected_traits={"tempo_range": [120, 190], "has_track_role": "drums", "min_quality_score": 50},
        notes="游戏战斗",
    ),
    EvalCase(
        id="lo_fi_hiphop",
        prompt="chill 的 lo-fi hiphop 伴奏",
        style_template_id="lo_fi_hiphop",
        expected_traits={"has_track_role": "bass", "has_track_role2": "drums", "min_quality_score": 50},
        notes="Lo-fi hiphop",
    ),
    EvalCase(
        id="ambient_meditation",
        prompt="安静祥和的冥想氛围音乐",
        style_template_id="ambient_meditation",
        expected_traits={"has_track_role": "pad", "min_quality_score": 50},
        notes="冥想氛围",
    ),
    EvalCase(
        id="electronic_pulse",
        prompt="节奏感强的电子舞曲",
        style_template_id="electronic_pulse",
        expected_traits={"tempo_range": [100, 160], "has_track_role": "drums", "min_quality_score": 50},
        notes="电子律动",
    ),
    EvalCase(
        id="rock_theme",
        prompt="强劲有力的摇滚主题曲",
        style_template_id="rock_theme",
        expected_traits={"has_track_role": "bass", "has_track_role2": "drums", "min_quality_score": 50},
        notes="摇滚主题",
    ),
]


def get_eval_cases() -> list[EvalCase]:
    """返回全部内置评估用例。"""
    return list(_CASES)
