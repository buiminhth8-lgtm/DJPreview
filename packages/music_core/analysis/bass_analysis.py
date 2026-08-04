"""贝斯质量辅助分析（T21）：轻量指标，不影响生成成功。"""

from __future__ import annotations

from packages.music_core.composer.events import NoteEvent


def bass_root_support_score(notes: list[NoteEvent], harmony_by_bar: dict[int, int]) -> float:
    """强拍根音支撑度 0-1：小节首拍贝斯音等于该小节和弦根音的比例。"""
    total = 0
    good = 0
    for note in notes:
        if note.start_beat % 4.0 < 0.05:
            bar = int(note.start_beat // 4) + 1
            root = harmony_by_bar.get(bar)
            if root is not None:
                total += 1
                if note.pitch % 12 == root % 12:
                    good += 1
    return round(good / total, 3) if total else 0.0


def bass_kick_alignment_score(
    bass_notes: list[NoteEvent],
    kick_positions: list[float],
    tolerance: float = 0.25,
) -> float:
    """主要 kick 附近存在贝斯音的比例 0-1。"""
    if not kick_positions:
        return 1.0
    aligned = 0
    for kick in kick_positions:
        if any(abs(n.start_beat - kick) <= tolerance for n in bass_notes):
            aligned += 1
    return round(aligned / len(kick_positions), 3)


def bass_motion_score(notes: list[NoteEvent]) -> float:
    """贝斯律动度 0-1：相邻音高变化归一化。"""
    if len(notes) < 2:
        return 0.0
    ordered = sorted(notes, key=lambda n: n.start_beat)
    moves = [abs(b.pitch - a.pitch) for a, b in zip(ordered, ordered[1:])]
    avg_move = sum(moves) / len(moves)
    return round(min(1.0, avg_move / 24.0), 3)


def chorus_bass_lift_detected(
    verse_notes: list[NoteEvent],
    chorus_notes: list[NoteEvent],
) -> bool:
    """chorus 贝斯数量/力度/音域跨度不低于 verse。"""
    if not verse_notes or not chorus_notes:
        return False
    avg_vel = lambda ns: sum(n.velocity for n in ns) / len(ns)
    span = lambda ns: max(n.pitch for n in ns) - min(n.pitch for n in ns)
    return (
        len(chorus_notes) >= len(verse_notes)
        and avg_vel(chorus_notes) >= avg_vel(verse_notes)
        and span(chorus_notes) >= span(verse_notes)
    )


def bass_range_validity(notes: list[NoteEvent], low: int = 24, high: int = 64) -> bool:
    """贝斯音区合法性。"""
    return bool(notes) and all(low <= n.pitch <= high for n in notes)
