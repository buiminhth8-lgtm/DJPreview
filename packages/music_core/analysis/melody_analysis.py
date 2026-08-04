"""旋律质量辅助分析（T18）：轻量指标，不阻塞生成、不改 QualityReport 结构。"""

from __future__ import annotations

from packages.music_core.composer.events import NoteEvent


def _bar_groups(notes: list[NoteEvent], beats_per_bar: int = 4) -> dict[int, list[NoteEvent]]:
    bars: dict[int, list[NoteEvent]] = {}
    for note in notes:
        bar = int(note.start_beat // beats_per_bar)
        bars.setdefault(bar, []).append(note)
    return bars


def _pattern(notes: list[NoteEvent], beats_per_bar: int) -> list[tuple[int, float, float]]:
    return [
        (n.pitch % 12, round(n.start_beat % beats_per_bar, 2), round(n.duration_beats, 2))
        for n in notes
    ]


def _pitch_classes(notes: list[NoteEvent]) -> set[int]:
    return {n.pitch % 12 for n in notes}


def motif_repetition_score(notes: list[NoteEvent], beats_per_bar: int = 4) -> float:
    """主题重复度 0-1：比较首小节与后续小节的 pitch-class 重叠率（集合级，稳健）。"""
    bars = _bar_groups(notes, beats_per_bar)
    if len(bars) < 2:
        return 0.0
    first_bar = min(bars)
    first = _pitch_classes(bars[first_bar])
    if not first:
        return 0.0
    totals = 0.0
    count = 0
    for bar in sorted(bars)[1:]:
        pc = _pitch_classes(bars[bar])
        if not pc:
            continue
        totals += len(first & pc) / len(first)
        count += 1
    return round(totals / count, 3) if count else 0.0


def phrase_balance_score(notes: list[NoteEvent], root_pitch: int, beats_per_bar: int = 4) -> float:
    """问答平衡度 0-1：2 小节为一组，统计后半组结尾音接近主音（±2 半音）的比例。"""
    bars = _bar_groups(notes, beats_per_bar)
    if len(bars) < 2:
        return 0.0
    ordered = sorted(bars)
    groups = [ordered[i : i + 2] for i in range(0, len(ordered), 2)]
    stable = 0
    total = 0
    for group in groups:
        if len(group) < 2:
            continue
        second = bars[group[1]]
        if not second:
            continue
        last = max(second, key=lambda n: n.start_beat)
        total += 1
        if abs((last.pitch % 12) - (root_pitch % 12)) <= 2:
            stable += 1
    return round(stable / total, 3) if total else 0.0


def chorus_lift_detected(
    verse_notes: list[NoteEvent],
    chorus_notes: list[NoteEvent],
    tolerance_pitch: float = 1.0,
    tolerance_velocity: float = 0.0,
) -> bool:
    """检测 chorus 相对 verse 是否提升：平均音高 / 力度 / 密度均不低于 verse（允许小幅容忍）。"""
    if not verse_notes or not chorus_notes:
        return False

    def _stats(notes):
        start = min(n.start_beat for n in notes)
        end = max(n.start_beat + n.duration_beats for n in notes)
        bars = max(1.0, (end - start) / 4.0)
        return (
            sum(n.pitch for n in notes) / len(notes),
            sum(n.velocity for n in notes) / len(notes),
            len(notes) / bars,
        )

    v_pitch, v_vel, v_density = _stats(verse_notes)
    c_pitch, c_vel, c_density = _stats(chorus_notes)
    return (
        c_pitch >= v_pitch - tolerance_pitch
        and c_vel >= v_vel - tolerance_velocity
        and c_density >= v_density
    )


def outro_theme_recall_detected(
    theme_notes: list[NoteEvent],
    outro_notes: list[NoteEvent],
    beats_per_bar: int = 4,
    threshold: float = 0.3,
) -> bool:
    """检测 outro 是否回收主题：outro 与主题首小节 pitch-class 集合重叠率超过阈值。"""
    if not theme_notes or not outro_notes:
        return False
    theme_bars = _bar_groups(theme_notes, beats_per_bar)
    outro_bars = _bar_groups(outro_notes, beats_per_bar)
    if not theme_bars or not outro_bars:
        return False
    first = _pitch_classes(theme_bars[min(theme_bars)])
    if not first:
        return False
    best = 0.0
    for bar in sorted(outro_bars):
        pc = _pitch_classes(outro_bars[bar])
        if not pc:
            continue
        best = max(best, len(first & pc) / len(first))
    return best >= threshold
