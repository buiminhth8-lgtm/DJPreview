"""编曲/声部进行质量辅助分析（T22）：轻量指标，不影响生成成功。"""

from __future__ import annotations

from packages.music_core.composer.events import NoteEvent


def voice_leading_smoothness_score(voicings: list[list[int]]) -> float:
    """声部进行平滑度 0-1：相邻 voicing 平均移动越小越高。"""
    if len(voicings) < 2:
        return 1.0
    moves: list[float] = []
    for prev, curr in zip(voicings, voicings[1:]):
        n = max(len(prev), len(curr))
        total = 0.0
        for i in range(n):
            a = prev[i] if i < len(prev) else prev[-1]
            b = curr[i] if i < len(curr) else curr[-1]
            total += abs(b - a)
        moves.append(total / n)
    avg = sum(moves) / len(moves)
    return round(max(0.0, min(1.0, 1.0 - avg / 14.0)), 3)


def arrangement_density_curve(notes: list[NoteEvent], beats_per_bar: int = 4) -> dict:
    """每 4 小节密度曲线。"""
    curve: dict[int, int] = {}
    for note in notes:
        group = int(note.start_beat // (beats_per_bar * 4))
        curve[group] = curve.get(group, 0) + 1
    return curve


def chorus_layer_lift_detected(verse_notes: list[NoteEvent], chorus_notes: list[NoteEvent]) -> bool:
    """chorus 声部数/数量/力度不低于 verse。"""
    if not verse_notes or not chorus_notes:
        return False
    avg_vel = lambda ns: sum(n.velocity for n in ns) / len(ns)
    return len(chorus_notes) >= len(verse_notes) and avg_vel(chorus_notes) >= avg_vel(verse_notes)


def pad_register_validity(notes: list[NoteEvent], low: int = 48, high: int = 84) -> bool:
    return bool(notes) and all(low <= n.pitch <= high for n in notes)


def strings_register_validity(notes: list[NoteEvent], low: int = 50, high: int = 88) -> bool:
    return bool(notes) and all(low <= n.pitch <= high for n in notes)


def section_entry_exit_score(notes_by_section: dict[str, list[NoteEvent]]) -> float:
    """段落进出度 0-1：每个段落都有背景层事件的比例。"""
    if not notes_by_section:
        return 0.0
    return round(sum(1 for notes in notes_by_section.values() if notes) / len(notes_by_section), 3)
