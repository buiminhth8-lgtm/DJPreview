"""主旋律引擎（T18）：motif + question/answer phrase + 段落变奏 + chorus lift + outro recall。"""

from __future__ import annotations

import random

from packages.music_core.composer.events import NoteEvent, beats_per_bar, section_energy
from packages.music_core.composer.melodic_theme import (
    MelodicMotif,
    force_stable_ending,
    generate_motif,
    motif_to_note_events,
    sparsify_motif,
    variant_motif,
)
from packages.music_core.composer.phrase_builder import (
    build_answer_phrase,
    build_question_phrase,
    phrase_to_motif,
)
from packages.music_core.composer.section_planner import bar_variant_pattern, melody_profile
from packages.music_core.harmony.harmony_engine import BarHarmony
from packages.music_core.theory.scales import get_scale_pitches
from services.api.schemas.music_spec import MusicSpec

_MIN_PITCH = 55
_MAX_PITCH = 88


class MelodyEngine:
    """按段落生成旋律：主题动机 + 问答句 + 段落轮廓（verse 克制 / chorus 提升 / outro 回收）。"""

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
        if not scale:
            scale = [60, 62, 64, 65, 67, 69, 71]
        root = scale[0]
        scale_degrees = sorted({p - root for p in scale})
        bpb = beats_per_bar(music_spec)

        sections: dict[str, list[BarHarmony]] = {}
        for bar in bar_harmony:
            sections.setdefault(bar.section_id, []).append(bar)
        if not sections:
            return []

        # 主题动机（1 小节）：基于第一小节的音阶与和弦
        first_bars = next(iter(sections.values()))
        seed_chord = first_bars[0].chord_pitches or [root, root + 4, root + 7]
        base_motif = generate_motif(
            scale,
            seed_chord,
            energy=0.6,
            density=0.55,
            rng=rng,
            length_bars=1,
            beats_per_bar=bpb,
        )

        notes: list[NoteEvent] = []
        for section_id, bars in sections.items():
            energy = section_energy(music_spec, section_id)
            profile = melody_profile(section_id, energy)
            pattern = bar_variant_pattern(profile["variant"])
            for bar_index, bar in enumerate(bars):
                variant = pattern[bar_index % len(pattern)]
                motif: MelodicMotif
                if variant in ("answer", "question"):
                    # 问答句：answer 稳定收束、question 悬而未决（进入 chorus 的张力）
                    chord_degrees = sorted({p - root for p in (bar.chord_pitches or [root]) if p - root >= 0})
                    if variant == "question":
                        phrase = build_question_phrase(scale_degrees, chord_degrees, rng, float(bpb))
                    else:
                        phrase = build_answer_phrase(scale_degrees, chord_degrees, rng, float(bpb))
                    motif = phrase_to_motif(phrase, float(bpb))
                else:
                    motif = variant_motif(base_motif, variant, rng)
                    if profile.get("sparse"):
                        motif = sparsify_motif(motif, rng, keep_ratio=0.55)

                start_beat = (bar.bar_index - 1) * bpb
                events = motif_to_note_events(
                    motif,
                    start_beat=start_beat,
                    root_pitch=root,
                    scale_degrees=scale_degrees,
                    velocity_base=profile["velocity_base"],
                    channel=channel,
                    pitch_min=_MIN_PITCH,
                    pitch_max=_MAX_PITCH,
                    pitch_shift=profile["pitch_shift"],
                )
                if profile.get("end_stable") and bar_index == len(bars) - 1:
                    events = force_stable_ending(
                        events,
                        start_beat + bpb,
                        bar.chord_pitches or [root],
                        root,
                        channel,
                    )
                notes.extend(events)
        return notes
