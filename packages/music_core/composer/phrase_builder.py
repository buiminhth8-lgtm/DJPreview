"""Question / Answer Phrase 构建（T18）。"""

from __future__ import annotations

import random

from packages.music_core.composer.melodic_theme import MelodicMotif, MotifNote, contour_of


def _stable_degrees(chord_degrees: list[int]) -> list[int]:
    """稳定收束度：主音 0 + 和弦音。"""
    return sorted({0, *(d for d in chord_degrees if d >= 0)})


def _unstable_degrees(scale_degrees: list[int], stable: list[int]) -> list[int]:
    """不稳定度：优先 2 / 7 / 9 度。"""
    preferred = [d for d in (2, 7, 9, 14) if d in scale_degrees and d not in stable]
    others = [d for d in scale_degrees if d not in stable and d not in preferred]
    result = preferred + others
    return result or list(scale_degrees)


def _build_phrase(
    scale_degrees: list[int],
    chord_degrees: list[int],
    rng: random.Random,
    length_beats: float,
    ending_degree: int,
    upward_bias: bool,
) -> list[MotifNote]:
    slots = [0.0, 0.75, 1.5, 2.25, 3.0, 3.5]
    notes: list[MotifNote] = []
    last: int | None = None
    for i, beat in enumerate(slots):
        if beat >= length_beats - 0.05:
            break
        next_beat = slots[i + 1] if (i + 1 < len(slots) and slots[i + 1] < length_beats) else length_beats
        if next_beat >= length_beats:
            degree = ending_degree
        else:
            strong = beat in (0.0, 2.0)
            candidates = list(chord_degrees) if (strong and chord_degrees) else list(scale_degrees)
            if upward_bias and last is not None:
                up = [d for d in candidates if d > last]
                if up:
                    candidates = up
            if last is not None:
                near = [d for d in candidates if abs(d - last) <= 5]
                if near:
                    candidates = near
            degree = rng.choice(candidates) if candidates else 0
        duration = max(0.5, min(0.75 if i < len(slots) - 1 else length_beats - beat, next_beat - beat))
        notes.append(
            MotifNote(
                scale_degree=degree,
                duration_beats=round(duration, 3),
                offset_beats=round(beat, 3),
                velocity=rng.randint(74, 88),
            )
        )
        last = degree
    if not notes:
        notes = [MotifNote(scale_degree=ending_degree, duration_beats=round(length_beats, 3), offset_beats=0.0, velocity=80)]
    return notes


def build_question_phrase(
    scale_degrees: list[int],
    chord_degrees: list[int],
    rng: random.Random,
    length_beats: float = 4.0,
) -> list[MotifNote]:
    """Question phrase：轮廓上行倾向，结尾落在不稳定度（2 / 5 / 7）。"""
    stable = _stable_degrees(chord_degrees)
    unstable = _unstable_degrees(scale_degrees, stable)
    ending = rng.choice(unstable) if unstable else 2
    return _build_phrase(scale_degrees, chord_degrees, rng, length_beats, ending, upward_bias=True)


def build_answer_phrase(
    scale_degrees: list[int],
    chord_degrees: list[int],
    rng: random.Random,
    length_beats: float = 4.0,
    question: list[MotifNote] | None = None,
) -> list[MotifNote]:
    """Answer phrase：结尾落在稳定音（1 / 3 / 5 或和弦音），更稳定。"""
    stable = _stable_degrees(chord_degrees)
    ending = stable[rng.randrange(len(stable))] if stable else 0
    return _build_phrase(scale_degrees, chord_degrees, rng, length_beats, ending, upward_bias=False)


def phrase_to_motif(notes: list[MotifNote], length_beats: float) -> MelodicMotif:
    """把 phrase 音符转成 MelodicMotif（约束不越界）。"""
    clamped = []
    for n in notes:
        offset = min(n.offset_beats, max(0.0, length_beats - 0.5))
        duration = min(n.duration_beats, max(0.5, length_beats - offset))
        clamped.append(
            MotifNote(
                scale_degree=n.scale_degree,
                duration_beats=round(duration, 3),
                offset_beats=round(offset, 3),
                velocity=n.velocity,
                octave_shift=n.octave_shift,
            )
        )
    return MelodicMotif(
        notes=tuple(clamped),
        length_beats=float(length_beats),
        contour=contour_of(clamped),
    )
