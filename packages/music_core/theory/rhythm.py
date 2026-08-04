"""节奏工具（T20）：swing timing 等。"""

from __future__ import annotations


def apply_swing(time_beats: float, swing: float, grid: float = 1.0) -> float:
    """对 offbeat（拍内中点，如 8 分音符的"and"）应用 swing 延迟。

    - swing=0 或 <=0.5：不做延迟（straight）。
    - swing 越大（0.5～1.0），offbeat 越晚。
    - 不产生负时间。
    """
    if swing <= 0.5 or grid <= 0:
        return float(time_beats)
    position = time_beats % grid
    offbeat = grid / 2.0
    if abs(position - offbeat) > 1e-6:
        return float(time_beats)
    delay = (swing - 0.5) * grid
    if delay <= 0:
        return float(time_beats)
    return round(time_beats + delay, 4)
