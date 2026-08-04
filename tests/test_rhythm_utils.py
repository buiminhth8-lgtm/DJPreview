"""T20：swing timing 工具测试。"""

from packages.music_core.composer.groove_library import style_swing
from packages.music_core.theory.rhythm import apply_swing


def test_swing_zero_unchanged():
    assert apply_swing(0.5, 0.0, 1.0) == 0.5
    assert apply_swing(1.75, 0.0, 1.0) == 1.75


def test_swing_delays_offbeat():
    assert apply_swing(0.5, 0.62, 1.0) > 0.5
    assert apply_swing(1.5, 0.6, 1.0) > 1.5


def test_onbeat_unchanged():
    assert apply_swing(1.0, 0.62, 1.0) == 1.0
    assert apply_swing(2.0, 0.62, 1.0) == 2.0


def test_swing_never_negative():
    for time in (0.25, 0.5, 1.75, 3.5):
        assert apply_swing(time, 0.62, 1.0) >= 0.0


def test_lo_fi_style_swing():
    assert style_swing("lo-fi") == 0.62
    assert style_swing("pop") == 0.5
    assert apply_swing(0.5, style_swing("lo-fi"), 1.0) > 0.5
