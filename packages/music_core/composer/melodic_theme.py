"""旋律主题模块（T18）：melodic motif / theme 的生成、变奏与渲染。

motif 使用 scale degree（相对主音的半音偏移）表达，不写死 MIDI pitch；
渲染时根据 key / mode / chord 量化为调内音，强拍优先落在和弦音。
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from packages.music_core.composer.events import NoteEvent


@dataclass(frozen=True)
class MotifNote:
    scale_degree: int
    duration_beats: float
    offset_beats: float
    velocity: int = 80
    octave_shift: int = 0


@dataclass(frozen=True)
class MelodicMotif:
    notes: tuple[MotifNote, ...]
    length_beats: float
    contour: str


def contour_of(notes) -> str:
    """根据 scale degree 序列计算轮廓。"""
    degrees = [n.scale_degree for n in notes]
    if len(degrees) < 2:
        return "static"
    diffs = [b - a for a, b in zip(degrees, degrees[1:])]
    ups = sum(1 for d in diffs if d > 0)
    downs = sum(1 for d in diffs if d < 0)
    if ups == 0 and downs == 0:
        return "static"
    if ups and downs:
        return "arch" if degrees[0] < degrees[-1] else "wave"
    return "ascending" if ups > downs else "descending"


def _clamped_note(note: MotifNote, length_beats: float) -> MotifNote:
    """约束 offset 与 duration 不越界。"""
    offset = min(note.offset_beats, max(0.0, length_beats - 0.5))
    duration = min(note.duration_beats, max(0.5, length_beats - offset))
    return MotifNote(
        scale_degree=note.scale_degree,
        duration_beats=round(max(0.5, duration), 3),
        offset_beats=round(offset, 3),
        velocity=note.velocity,
        octave_shift=note.octave_shift,
    )


def generate_motif(
    scale_pitches: list[int],
    chord_pitches: list[int],
    energy: float,
    density: float,
    rng: random.Random,
    length_bars: int = 1,
    beats_per_bar: int = 4,
) -> MelodicMotif:
    """生成 1～2 小节 melodic motif（scale degree 表达，强拍落和弦音）。"""
    root = scale_pitches[0] if scale_pitches else 60
    scale_degrees = sorted({p - root for p in scale_pitches})
    scale_degrees += [d + 12 for d in scale_degrees]
    chord_degrees = sorted({p - root for p in chord_pitches if p - root >= 0})
    if not scale_degrees:
        scale_degrees = [0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19]

    length = length_bars * beats_per_bar
    slots = [round(i * 0.5, 3) for i in range(int(length * 2))]
    notes: list[MotifNote] = []
    last: int | None = None
    for i, beat in enumerate(slots):
        strong = (beat % beats_per_bar) == 0
        if not strong and rng.random() > max(0.1, min(0.9, density)):
            continue
        candidates = chord_degrees if (strong and chord_degrees) else scale_degrees
        if last is not None:
            near = [d for d in candidates if abs(d - last) <= 7]
            if near:
                candidates = near
        degree = candidates[rng.randrange(len(candidates))]
        next_beat = slots[i + 1] if i + 1 < len(slots) else length
        duration = 1.0 if rng.random() < 0.6 else 0.5
        if i == len(slots) - 1:
            duration = max(0.5, length - beat)
        else:
            duration = min(duration, max(0.5, next_beat - beat))
        notes.append(
            MotifNote(
                scale_degree=degree,
                duration_beats=round(duration, 3),
                offset_beats=beat,
                velocity=80,
            )
        )
        last = degree

    if not notes:
        notes = [MotifNote(scale_degree=0, duration_beats=float(length), offset_beats=0.0, velocity=80)]
    return MelodicMotif(
        notes=tuple(_clamped_note(n, length) for n in notes),
        length_beats=float(length),
        contour=contour_of(notes),
    )


def variant_motif(motif: MelodicMotif, variant: str, rng: random.Random) -> MelodicMotif:
    """主题变奏：repeat / sequence_up / sequence_down / ornament / simplify / intensify / invert_contour / rhythm_variation。"""
    notes = [
        MotifNote(
            scale_degree=n.scale_degree,
            duration_beats=n.duration_beats,
            offset_beats=n.offset_beats,
            velocity=n.velocity,
            octave_shift=n.octave_shift,
        )
        for n in motif.notes
    ]

    if variant == "sequence_up":
        notes = [MotifNote(scale_degree=n.scale_degree + 7, duration_beats=n.duration_beats, offset_beats=n.offset_beats, velocity=n.velocity) for n in notes]
    elif variant == "sequence_down":
        notes = [MotifNote(scale_degree=n.scale_degree - 7, duration_beats=n.duration_beats, offset_beats=n.offset_beats, velocity=n.velocity) for n in notes]
    elif variant == "ornament":
        decorated: list[MotifNote] = []
        for n in notes:
            if rng.random() < 0.35:
                step = rng.choice([-2, -1, 1, 2])
                decorated.append(
                    MotifNote(
                        scale_degree=n.scale_degree + step,
                        duration_beats=0.5,
                        offset_beats=max(0.0, n.offset_beats - 0.25),
                        velocity=n.velocity,
                    )
                )
            decorated.append(n)
        notes = sorted(decorated, key=lambda x: x.offset_beats)
    elif variant == "simplify":
        notes = [n for n in notes if n.offset_beats % 1 == 0 or rng.random() > 0.5]
    elif variant == "intensify":
        extra: list[MotifNote] = []
        for i in range(len(notes) - 1):
            if rng.random() < 0.35:
                left, right = notes[i], notes[i + 1]
                mid = round((left.offset_beats + right.offset_beats) / 2, 3)
                if left.offset_beats < mid < right.offset_beats:
                    extra.append(
                        MotifNote(scale_degree=left.scale_degree, duration_beats=0.5, offset_beats=mid, velocity=left.velocity)
                    )
        notes = sorted(notes + extra, key=lambda x: x.offset_beats)
    elif variant == "invert_contour" and notes:
        base = notes[0].scale_degree
        notes = [
            MotifNote(scale_degree=base + (base - n.scale_degree), duration_beats=n.duration_beats, offset_beats=n.offset_beats, velocity=n.velocity)
            for n in notes
        ]
    elif variant == "rhythm_variation":
        shifted: list[MotifNote] = []
        for n in notes:
            if rng.random() < 0.4:
                shifted.append(
                    MotifNote(
                        scale_degree=n.scale_degree,
                        duration_beats=max(0.5, n.duration_beats),
                        offset_beats=n.offset_beats + 0.5,
                        velocity=n.velocity,
                    )
                )
            else:
                shifted.append(n)
        notes = sorted(shifted, key=lambda x: x.offset_beats)
    # repeat / 未知变奏：保持原样

    if not notes:
        notes = [MotifNote(scale_degree=0, duration_beats=2.0, offset_beats=0.0, velocity=80)]
    return MelodicMotif(
        notes=tuple(_clamped_note(n, motif.length_beats) for n in notes),
        length_beats=motif.length_beats,
        contour=contour_of(notes),
    )


def sparsify_motif(motif: MelodicMotif, rng: random.Random, keep_ratio: float = 0.6) -> MelodicMotif:
    """稀疏化：保留整拍音，弱拍按比例保留（用于 intro / outro）。"""
    strong = [n for n in motif.notes if n.offset_beats % 1 == 0]
    weak = [n for n in motif.notes if n.offset_beats % 1 != 0]
    kept = [n for n in weak if rng.random() < keep_ratio]
    result = sorted(strong + kept, key=lambda x: x.offset_beats)
    if not result:
        result = [MotifNote(scale_degree=0, duration_beats=2.0, offset_beats=0.0, velocity=70)]
    return MelodicMotif(
        notes=tuple(_clamped_note(n, motif.length_beats) for n in result),
        length_beats=motif.length_beats,
        contour=contour_of(result),
    )


def _nearest_scale_pitch(
    target: int,
    root: int,
    scale_degrees: list[int],
    pitch_min: int,
    pitch_max: int,
) -> int | None:
    """把目标音高量化到最近的调内音。"""
    degrees = list(scale_degrees) or [0, 2, 4, 5, 7, 9, 11]
    candidates = []
    for degree in degrees:
        for octave_shift in range(-3, 4):
            pitch = root + degree + 12 * octave_shift
            if pitch_min <= pitch <= pitch_max:
                candidates.append(pitch)
    if not candidates:
        return None
    return min(candidates, key=lambda p: abs(p - target))


def motif_to_note_events(
    motif: MelodicMotif,
    *,
    start_beat: float,
    root_pitch: int,
    scale_degrees: list[int],
    velocity_base: int,
    channel: int,
    pitch_min: int = 55,
    pitch_max: int = 88,
    pitch_shift: int = 0,
) -> list[NoteEvent]:
    """把 motif 渲染为 NoteEvent：音高量化到调内音，velocity 基于段落基准。"""
    events: list[NoteEvent] = []
    for note in motif.notes:
        target = root_pitch + note.scale_degree + pitch_shift + 12 * note.octave_shift
        pitch = _nearest_scale_pitch(target, root_pitch, scale_degrees, pitch_min, pitch_max)
        if pitch is None:
            continue
        velocity = velocity_base + (note.velocity - 80)
        events.append(
            NoteEvent(
                pitch=pitch,
                start_beat=round(start_beat + note.offset_beats, 3),
                duration_beats=round(max(0.05, note.duration_beats), 3),
                velocity=max(1, min(127, int(round(velocity)))),
                channel=channel,
            )
        )
    return events


def force_stable_ending(
    events: list[NoteEvent],
    bar_end_beat: float,
    chord_pitches: list[int],
    root: int,
    channel: int,
) -> list[NoteEvent]:
    """把小节结尾改为稳定和弦音并落在小节末（outro / chorus 收尾）。"""
    if not events:
        pitch = (chord_pitches or [root])[0]
        return [NoteEvent(pitch=pitch, start_beat=round(bar_end_beat - 1.0, 3), duration_beats=1.0, velocity=76, channel=channel)]
    last = max(events, key=lambda e: e.start_beat)
    stable = sorted({p for p in (chord_pitches or [root])})
    pitch = min(stable, key=lambda p: abs(p - last.pitch)) if stable else root
    adjusted = [e for e in events if e is not last]
    adjusted.append(
        NoteEvent(
            pitch=pitch,
            start_beat=round(bar_end_beat - 1.0, 3),
            duration_beats=1.0,
            velocity=max(last.velocity, 70),
            channel=channel,
        )
    )
    return sorted(adjusted, key=lambda e: e.start_beat)
