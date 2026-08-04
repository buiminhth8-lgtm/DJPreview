"""主旋律引擎：基于调式音阶与和弦音生成旋律。"""

from __future__ import annotations

import random

from packages.music_core.composer.events import NoteEvent, beats_per_bar, section_energy
from packages.music_core.harmony.harmony_engine import BarHarmony
from packages.music_core.theory.scales import get_scale_pitches
from services.api.schemas.music_spec import MusicSpec

_MIN_PITCH = 55
_MAX_PITCH = 88


def _clamp_pitch(pitch: int) -> int:
    return max(0, min(127, pitch))


class MelodyEngine:
    """根据 MusicSpec 与 BarHarmony 生成主旋律 NoteEvent 列表。"""

    def generate(
        self,
        music_spec: MusicSpec,
        bar_harmony: list[BarHarmony],
        channel: int = 0,
    ) -> list[NoteEvent]:
        rng = random.Random(music_spec.seed)
        key = music_spec.tonality.key
        mode = music_spec.tonality.mode or "major"
        scale = list(get_scale_pitches(key, mode, octave=4))
        scale += [p + 12 for p in scale]
        scale = sorted({p for p in scale if _MIN_PITCH <= p <= _MAX_PITCH})
        if not scale:
            scale = list(range(60, 85))

        bpb = beats_per_bar(music_spec)
        notes: list[NoteEvent] = []
        last_pitch: int | None = None
        repeat_count = 0
        outro_id = music_spec.form[-1].id if music_spec.form else None

        for bar in bar_harmony:
            energy = section_energy(music_spec, bar.section_id)
            is_outro = bar.section_id == "outro" or (outro_id is not None and bar.section_id == outro_id)
            density = 2 + int(energy * 5)
            if is_outro:
                density = max(1, density - 2)
            velocity = int(62 + energy * 36)
            chord = bar.chord_pitches or [60, 64, 67]
            bar_start = (bar.bar_index - 1) * bpb
            slots = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]

            chosen = [0]
            if density > 1:
                chosen += rng.sample(range(1, 8), min(density - 1, 7))
            chosen.sort()

            for slot_idx in chosen:
                beat = slots[slot_idx]
                strong = slot_idx in (0, 4)
                if strong:
                    pitch = self._pick_chord_tone(chord, rng, last_pitch, high_bias=energy >= 0.7)
                else:
                    pitch = self._pick_scale_tone(scale, rng, last_pitch)
                if pitch == last_pitch:
                    repeat_count += 1
                else:
                    repeat_count = 0
                if repeat_count >= 2:
                    pitch = self._pick_scale_tone(scale, rng, last_pitch, avoid=last_pitch)
                    repeat_count = 0
                last_pitch = pitch

                if slot_idx == 7 or rng.random() < 0.18:
                    duration = 2.0
                else:
                    duration = 0.5 if rng.random() < 0.7 else 1.0
                notes.append(
                    NoteEvent(
                        pitch=_clamp_pitch(pitch),
                        start_beat=round(bar_start + beat, 3),
                        duration_beats=round(duration, 3),
                        velocity=velocity,
                        channel=channel,
                    )
                )
        return notes

    def _pick_chord_tone(self, chord: list[int], rng: random.Random, last_pitch: int | None, high_bias: bool) -> int:
        candidates = list(chord) + [p + 12 for p in chord] + [p - 12 for p in chord]
        if high_bias:
            candidates = [p for p in candidates if p >= 67]
        candidates = [p for p in candidates if _MIN_PITCH <= p <= _MAX_PITCH]
        if not candidates:
            candidates = [60, 64, 67, 72]
        return self._nearest(candidates, rng, last_pitch)

    def _pick_scale_tone(self, scale: list[int], rng: random.Random, last_pitch: int | None, avoid: int | None = None) -> int:
        candidates = [p for p in scale if p != avoid]
        if not candidates:
            candidates = list(scale)
        return self._nearest(candidates, rng, last_pitch, max_step=7)

    @staticmethod
    def _nearest(candidates: list[int], rng: random.Random, last_pitch: int | None, max_step: int | None = None) -> int:
        if last_pitch is None:
            return candidates[rng.randrange(len(candidates))]
        if max_step is not None:
            near = [p for p in candidates if abs(p - last_pitch) <= max_step]
            if near:
                candidates = near
        candidates = sorted(candidates, key=lambda p: abs(p - last_pitch))
        pool = candidates[:3]
        return pool[rng.randrange(len(pool))]
