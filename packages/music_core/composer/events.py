"""内部编曲数据结构。"""

from __future__ import annotations

from dataclasses import dataclass, field

from services.api.schemas.music_spec import MusicSpec


@dataclass
class NoteEvent:
    """单个音符事件。"""

    pitch: int
    start_beat: float
    duration_beats: float
    velocity: int
    channel: int
    is_drum: bool = False


@dataclass
class TrackEvents:
    """一条编曲轨道的全部音符。"""

    track_id: str
    name: str
    role: str
    instrument: str
    channel: int
    program: int | None
    notes: list[NoteEvent] = field(default_factory=list)
    pan: int | None = field(default=None)


@dataclass
class CompositionResult:
    """一次完整编曲的结果。"""

    song_id: str | None = None
    title: str = ""
    bpm: int = 120
    ticks_per_beat: int = 480
    total_bars: int = 0
    beats_per_bar: int = 4
    tracks: list[TrackEvents] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def beats_per_bar(music_spec: MusicSpec) -> int:
    """返回每小节拍数（本阶段保证 4/4 可用，其他拍号按 numerator 处理）。"""
    if music_spec.meter.denominator == 4:
        return max(1, music_spec.meter.numerator)
    return 4


def section_energy(music_spec: MusicSpec, section_id: str, default: float = 0.6) -> float:
    """返回段落 energy（0-1），找不到时用默认值。"""
    for section in music_spec.form:
        if section.id == section_id:
            return max(0.0, min(1.0, section.energy))
    return default
