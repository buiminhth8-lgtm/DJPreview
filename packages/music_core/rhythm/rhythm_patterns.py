"""基础节奏模板（以 beat 为单位，默认 4/4，每小节 4 拍）。"""

from __future__ import annotations

from typing import Callable

# 音高类节奏：[(beat, duration_beats, velocity_scale)]
PitchedPattern = list[tuple[float, float, float]]

# 鼓组节奏：{midi_note: [(beat, duration_beats, velocity_scale)]}
DrumPattern = dict[int, list[tuple[float, float, float]]]


# ---------- 音高类节奏模板 ----------

def block_chords() -> PitchedPattern:
    """整组和弦块状和弦：第 1、3 拍。"""
    return [(0.0, 2.0, 1.0), (2.0, 2.0, 0.9)]


def arpeggio() -> PitchedPattern:
    """分解和弦：每拍一个音。"""
    return [(0.0, 1.0, 1.0), (1.0, 1.0, 0.8), (2.0, 1.0, 0.9), (3.0, 1.0, 0.75)]


def broken_chords() -> PitchedPattern:
    """半分解和弦：低音 + 高音交替。"""
    return [
        (0.0, 0.5, 1.0),
        (0.5, 0.5, 0.8),
        (1.0, 1.0, 0.85),
        (2.0, 0.5, 0.95),
        (2.5, 0.5, 0.8),
        (3.0, 1.0, 0.85),
    ]


def sustained_pad() -> PitchedPattern:
    """铺底长音：整小节。"""
    return [(0.0, 4.0, 1.0)]


def long_chords() -> PitchedPattern:
    """Pad / Strings 长和弦：与 sustained_pad 相同。"""
    return sustained_pad()


def simple_bass() -> PitchedPattern:
    """简单贝斯：第 1、3 拍根音。"""
    return [(0.0, 1.5, 1.0), (2.0, 1.5, 0.85)]


# ---------- 鼓组节奏模板 ----------

def pop_drums() -> DrumPattern:
    """流行鼓：底鼓 1、3 拍，军鼓 2、4 拍，八分踩镲。"""
    return {
        36: [(0.0, 0.4, 1.0), (2.0, 0.4, 0.95)],
        38: [(1.0, 0.4, 1.0), (3.0, 0.4, 0.95)],
        42: [
            (0.0, 0.2, 0.8), (0.5, 0.2, 0.7), (1.0, 0.2, 0.8), (1.5, 0.2, 0.7),
            (2.0, 0.2, 0.8), (2.5, 0.2, 0.7), (3.0, 0.2, 0.8), (3.5, 0.2, 0.7),
        ],
    }


def rock_drums() -> DrumPattern:
    """摇滚鼓：底鼓更密，军鼓 2、4 拍。"""
    return {
        36: [(0.0, 0.4, 1.0), (1.0, 0.2, 0.8), (2.0, 0.4, 1.0), (3.0, 0.2, 0.8)],
        38: [(1.0, 0.4, 1.0), (3.0, 0.4, 1.0)],
        42: [
            (0.0, 0.15, 0.85), (0.5, 0.15, 0.75), (1.0, 0.15, 0.85), (1.5, 0.15, 0.75),
            (2.0, 0.15, 0.85), (2.5, 0.15, 0.75), (3.0, 0.15, 0.85), (3.5, 0.15, 0.75),
        ],
    }


def lo_fi_drums() -> DrumPattern:
    """Lo-fi 鼓：密度低、力度轻。"""
    return {
        36: [(0.0, 0.4, 0.95), (2.0, 0.4, 0.85)],
        38: [(1.0, 0.4, 0.7), (3.0, 0.4, 0.65)],
        42: [(0.0, 0.2, 0.55), (1.0, 0.2, 0.5), (2.0, 0.2, 0.55), (3.0, 0.2, 0.5)],
    }


def electronic_drums() -> DrumPattern:
    """电子鼓：四踩底鼓 + 十六分踩镲。"""
    return {
        36: [(0.0, 0.2, 1.0), (1.0, 0.2, 0.9), (2.0, 0.2, 1.0), (3.0, 0.2, 0.9)],
        38: [(1.0, 0.2, 0.95), (3.0, 0.2, 0.95)],
        42: [
            (0.0, 0.1, 0.8), (0.25, 0.1, 0.7), (0.5, 0.1, 0.8), (0.75, 0.1, 0.7),
            (1.0, 0.1, 0.8), (1.25, 0.1, 0.7), (1.5, 0.1, 0.8), (1.75, 0.1, 0.7),
            (2.0, 0.1, 0.8), (2.25, 0.1, 0.7), (2.5, 0.1, 0.8), (2.75, 0.1, 0.7),
            (3.0, 0.1, 0.8), (3.25, 0.1, 0.7), (3.5, 0.1, 0.8), (3.75, 0.1, 0.7),
        ],
    }


def cinematic_drums() -> DrumPattern:
    """电影感鼓：稀疏低频 + 撞击。"""
    return {
        36: [(0.0, 0.5, 1.0), (2.5, 0.4, 0.9)],
        49: [(0.0, 0.3, 0.8)],
        42: [(2.5, 0.2, 0.6)],
    }


PITCHED_PATTERNS: dict[str, Callable[[], PitchedPattern]] = {
    "block_chords": block_chords,
    "arpeggio": arpeggio,
    "broken_chords": broken_chords,
    "sustained_pad": sustained_pad,
    "long_chords": long_chords,
    "simple_bass": simple_bass,
}

DRUM_PATTERNS: dict[str, Callable[[], DrumPattern]] = {
    "pop": pop_drums,
    "rock": rock_drums,
    "lo-fi": lo_fi_drums,
    "electronic": electronic_drums,
    "cinematic": cinematic_drums,
}
