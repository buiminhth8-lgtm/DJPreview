"""段落旋律规划（T18）：不同 section 的旋律轮廓参数。"""

from __future__ import annotations


def melody_profile(section_id: str, energy: float) -> dict:
    """返回段落旋律参数。

    字段：velocity_base / density / pitch_shift（半音）/ variant / recall（主题回收）/
    end_stable（结尾稳定音）/ sparse（稀疏）。
    """
    e = max(0.0, min(1.0, energy))
    sid = (section_id or "").strip().lower()
    if sid in ("intro", "前奏"):
        return {
            "velocity_base": 62,
            "density": 0.3,
            "pitch_shift": -2,
            "variant": "simplify",
            "recall": False,
            "end_stable": False,
            "sparse": True,
        }
    if sid in ("verse", "主歌"):
        return {
            "velocity_base": 72 + int(e * 10),
            "density": 0.4,
            "pitch_shift": 0,
            "variant": "repeat",
            "recall": True,
            "end_stable": False,
            "sparse": False,
        }
    if sid in ("pre_chorus", "prechorus", "前副歌"):
        return {
            "velocity_base": 78 + int(e * 12),
            "density": 0.55,
            "pitch_shift": 2,
            "variant": "sequence_up",
            "recall": False,
            "end_stable": False,
            "sparse": False,
        }
    if sid in ("chorus", "副歌"):
        return {
            "velocity_base": 86 + int(e * 20),
            "density": 0.6,
            "pitch_shift": 3,
            "variant": "intensify",
            "recall": True,
            "end_stable": True,
            "sparse": False,
        }
    if sid in ("bridge", "桥段"):
        return {
            "velocity_base": 74 + int(e * 16),
            "density": 0.45,
            "pitch_shift": 1,
            "variant": "invert_contour",
            "recall": False,
            "end_stable": False,
            "sparse": False,
        }
    if sid in ("outro", "尾奏"):
        return {
            "velocity_base": 64 + int(e * 12),
            "density": 0.3,
            "pitch_shift": -2,
            "variant": "simplify",
            "recall": True,
            "end_stable": True,
            "sparse": True,
        }
    return {
        "velocity_base": 72 + int(e * 16),
        "density": 0.5,
        "pitch_shift": 0,
        "variant": "repeat",
        "recall": False,
        "end_stable": False,
        "sparse": False,
    }


def bar_variant_pattern(variant: str) -> list[str]:
    """每 4 小节主题循环：A / A' / B / A''，B 可为 answer / question 句。"""
    patterns = {
        "repeat": ["repeat", "ornament", "answer", "repeat"],
        "intensify": ["intensify", "intensify", "answer", "intensify"],
        "simplify": ["simplify", "repeat", "simplify", "repeat"],
        "invert_contour": ["invert_contour", "sequence_down", "ornament", "sequence_up"],
        "sequence_up": ["sequence_up", "ornament", "question", "sequence_up"],
    }
    return patterns.get(variant, ["repeat", "ornament", "sequence_up", "intensify"])
