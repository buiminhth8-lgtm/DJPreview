"""Motif Engine：可复现的旋律动机生成、变换与渲染。"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from packages.music_core.composer.events import NoteEvent
from packages.music_core.generation.generation_context import GenerationContext


@dataclass
class MotifNote:
    degree: int  # 相对主音的半音偏移（0=主音，允许跨八度）
    duration_beats: float
    offset_beats: float
    accent: bool = False


@dataclass
class Motif:
    id: str
    length_beats: float
    notes: list[MotifNote]
    contour: str
    density: float
    energy: float


def _contour(degrees: list[int]) -> str:
    if len(degrees) < 2:
        return "static"
    diffs = [b - a for a, b in zip(degrees, degrees[1:])]
    ups = sum(1 for d in diffs if d > 0)
    downs = sum(1 for d in diffs if d < 0)
    if ups == 0 and downs == 0:
        return "static"
    if ups and downs:
        return "arch" if degrees[0] < degrees[-1] else "wave"
    return "rising" if ups > downs else "falling"


def create_motif(
    scale_pitches: list[int],
    chord_pitches: list[int],
    energy: float,
    density: float,
    rng: random.Random,
) -> Motif:
    """基于音阶与和弦音生成 1 小节（4 拍）动机，强拍落和弦音。"""
    root = scale_pitches[0] if scale_pitches else 60
    scale_degrees = sorted({p - root for p in scale_pitches})
    scale_degrees += [d + 12 for d in scale_degrees]
    chord_degrees = sorted({p - root for p in chord_pitches if p - root >= 0})
    if not scale_degrees:
        scale_degrees = [0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19]

    slots = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
    notes: list[MotifNote] = []
    last_degree: int | None = None
    for i, beat in enumerate(slots):
        strong = i in (0, 4)
        if not strong and rng.random() > max(0.15, min(0.85, density)):
            continue
        candidates = chord_degrees if (strong and chord_degrees) else scale_degrees
        if last_degree is not None:
            near = [d for d in candidates if abs(d - last_degree) <= 7]
            if near:
                candidates = near
        degree = candidates[rng.randrange(len(candidates))]
        duration = 0.5 if rng.random() < 0.6 else 1.0
        if i == 7:
            duration = 2.0
        notes.append(MotifNote(degree=degree, duration_beats=duration, offset_beats=beat, accent=strong))
        last_degree = degree

    if not notes:
        notes = [MotifNote(degree=0, duration_beats=2.0, offset_beats=0.0, accent=True)]

    return Motif(
        id=f"m{rng.randrange(10**6):06d}",
        length_beats=4.0,
        notes=notes,
        contour=_contour([n.degree for n in notes]),
        density=round(len(notes) / 8, 3),
        energy=round(max(0.0, min(1.0, energy)), 3),
    )


def transform_motif(motif: Motif, transform_type: str, rng: random.Random) -> Motif:
    """变换动机：repeat / sequence_up / sequence_down / rhythm_variation / ornament / simplify / intensify / invert_contour。"""
    notes = [MotifNote(degree=n.degree, duration_beats=n.duration_beats, offset_beats=n.offset_beats, accent=n.accent) for n in motif.notes]

    if transform_type == "sequence_up":
        notes = [MotifNote(degree=n.degree + 7, duration_beats=n.duration_beats, offset_beats=n.offset_beats, accent=n.accent) for n in notes]
    elif transform_type == "sequence_down":
        notes = [MotifNote(degree=n.degree - 7, duration_beats=n.duration_beats, offset_beats=n.offset_beats, accent=n.accent) for n in notes]
    elif transform_type == "rhythm_variation":
        for n in notes:
            if rng.random() < 0.5:
                n.offset_beats = round(n.offset_beats + 0.1, 3)
            if rng.random() < 0.3:
                n.duration_beats = round(max(0.5, n.duration_beats * 2), 3)
    elif transform_type == "ornament":
        decorated: list[MotifNote] = []
        for n in notes:
            if rng.random() < 0.35:
                step = rng.choice([-2, -1, 1, 2])
                decorated.append(
                    MotifNote(degree=n.degree + step, duration_beats=0.5, offset_beats=max(0.0, n.offset_beats - 0.25), accent=False)
                )
            decorated.append(n)
        notes = decorated
    elif transform_type == "simplify":
        notes = [n for n in notes if n.accent or rng.random() > 0.45]
    elif transform_type == "intensify":
        extra: list[MotifNote] = []
        for i in range(len(notes) - 1):
            if rng.random() < 0.35:
                left, right = notes[i], notes[i + 1]
                mid = round((left.offset_beats + right.offset_beats) / 2, 3)
                extra.append(MotifNote(degree=left.degree, duration_beats=0.5, offset_beats=mid, accent=False))
        notes = sorted(notes + extra, key=lambda x: x.offset_beats)
    elif transform_type == "invert_contour" and notes:
        base = notes[0].degree
        notes = [MotifNote(degree=base + (base - n.degree), duration_beats=n.duration_beats, offset_beats=n.offset_beats, accent=n.accent) for n in notes]
    # repeat 与其他未知变换：保持原样

    if not notes:
        notes = [MotifNote(degree=0, duration_beats=2.0, offset_beats=0.0, accent=True)]
    return Motif(
        id=f"t{rng.randrange(10**6):06d}",
        length_beats=motif.length_beats,
        notes=notes,
        contour=_contour([n.degree for n in notes]),
        density=round(len(notes) / max(motif.length_beats, 1), 3),
        energy=motif.energy,
    )


def _nearest_scale_pitch(
    target: int,
    root: int,
    scale_degrees: list[int],
    pitch_min: int,
    pitch_max: int,
) -> int | None:
    """把目标音高量化到最近的音阶音（保证调内）。"""
    degrees = list(scale_degrees) or [0, 2, 4, 5, 7, 9, 11]
    candidates = []
    for degree in degrees:
        for octave_shift in range(-2, 3):
            pitch = root + degree + 12 * octave_shift
            if pitch_min <= pitch <= pitch_max:
                candidates.append(pitch)
    if not candidates:
        return None
    return min(candidates, key=lambda p: abs(p - target))


def motif_to_note_events(motif: Motif, context: GenerationContext) -> list[NoteEvent]:
    """把动机渲染为 NoteEvent（音高量化到调内音阶，accent 增加力度）。"""
    events: list[NoteEvent] = []
    for note in motif.notes:
        target = context.root_pitch + note.degree
        pitch = _nearest_scale_pitch(target, context.root_pitch, context.scale_degrees, context.pitch_min, context.pitch_max)
        if pitch is None:
            continue
        velocity = context.velocity + (12 if note.accent else 0)
        events.append(
            NoteEvent(
                pitch=pitch,
                start_beat=round(context.start_beat + note.offset_beats, 3),
                duration_beats=round(note.duration_beats, 3),
                velocity=max(1, min(127, velocity)),
                channel=context.channel,
            )
        )
    return events
