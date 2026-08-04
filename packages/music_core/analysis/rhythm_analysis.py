"""鼓组/节奏质量辅助分析（T20）：轻量指标，不影响生成成功。"""

from __future__ import annotations

from packages.music_core.composer.events import NoteEvent

_DRUM_NOTES = {36, 38, 39, 42, 44, 45, 46, 47, 49, 50, 51}


def _drum_notes(notes: list[NoteEvent]) -> list[NoteEvent]:
    return [n for n in notes if n.pitch in _DRUM_NOTES or n.is_drum]


def drum_density_score(notes: list[NoteEvent], beats_per_bar: int = 4) -> float:
    """每小节鼓点密度（hits/bar）。"""
    drums = _drum_notes(notes)
    if not drums:
        return 0.0
    start = min(n.start_beat for n in drums)
    end = max(n.start_beat + n.duration_beats for n in drums)
    bars = max(1.0, (end - start) / beats_per_bar)
    return round(len(drums) / bars, 3)


def section_fill_detected(notes: list[NoteEvent], beats_per_bar: int = 4) -> bool:
    """检测小节末尾（后 1 拍）是否存在 >=3 个连续鼓点（fill 特征）。"""
    drums = _drum_notes(notes)
    for bar_start in range(0, 200):
        tail = [
            n
            for n in drums
            if (bar_start * beats_per_bar) <= n.start_beat < (bar_start + 1) * beats_per_bar
            and n.start_beat % beats_per_bar >= beats_per_bar - 1
        ]
        if len(tail) >= 3:
            return True
    return False


def chorus_intensity_lift_detected(verse_notes: list[NoteEvent], chorus_notes: list[NoteEvent]) -> bool:
    """chorus 鼓点数量/平均力度不低于 verse。"""
    verse = _drum_notes(verse_notes)
    chorus = _drum_notes(chorus_notes)
    if not verse or not chorus:
        return False
    return len(chorus) >= len(verse) and (sum(n.velocity for n in chorus) / len(chorus)) >= (
        sum(n.velocity for n in verse) / len(verse)
    )


def swing_feel_detected(notes: list[NoteEvent]) -> bool:
    """检测 offbeat 事件是否出现 swing 位移（非 0.5 网格上的踩镲）。"""
    drums = _drum_notes(notes)
    for note in drums:
        pos = round(note.start_beat % 1.0, 3)
        if pos not in (0.0, 0.25, 0.5, 0.75) and 0.05 < pos < 0.95:
            return True
    return False


def velocity_variation_score(notes: list[NoteEvent]) -> float:
    """力度变化度 0-1：velocity 标准差归一化。"""
    drums = _drum_notes(notes)
    if len(drums) < 2:
        return 0.0
    velocities = [n.velocity for n in drums]
    mean = sum(velocities) / len(velocities)
    variance = sum((v - mean) ** 2 for v in velocities) / len(velocities)
    return round(min(1.0, variance ** 0.5 / 40.0), 3)
