"""主旋律引擎：基于 Motif Engine 生成可复现、有动机感的旋律。"""

from __future__ import annotations

import random

from packages.music_core.composer.events import NoteEvent, beats_per_bar, section_energy
from packages.music_core.generation.generation_context import GenerationContext
from packages.music_core.harmony.harmony_engine import BarHarmony
from packages.music_core.theory.scales import get_scale_pitches
from services.api.schemas.music_spec import MusicSpec

_MIN_PITCH = 55
_MAX_PITCH = 88


class MelodyEngine:
    """按段落生成动机并做 repeat / sequence / intensify / simplify 等变换。"""

    def generate(
        self,
        music_spec: MusicSpec,
        bar_harmony: list[BarHarmony],
        channel: int = 0,
    ) -> list[NoteEvent]:
        # 延迟导入：避免 generation → motif_engine → composer → music_composer → melody_engine 循环
        from packages.music_core.generation.motif_engine import create_motif, motif_to_note_events, transform_motif

        rng = random.Random(music_spec.seed)
        key = music_spec.tonality.key
        mode = music_spec.tonality.mode or "major"
        scale = list(get_scale_pitches(key, mode, octave=4))
        if not scale:
            scale = [60, 62, 64, 65, 67, 69, 71]
        root = scale[0]
        scale_degrees = sorted({p - root for p in scale})
        bpb = beats_per_bar(music_spec)
        outro_id = music_spec.form[-1].id if music_spec.form else None

        sections: dict[str, list[BarHarmony]] = {}
        for bar in bar_harmony:
            sections.setdefault(bar.section_id, []).append(bar)

        notes: list[NoteEvent] = []
        for section_id, bars in sections.items():
            energy = section_energy(music_spec, section_id)
            density = 0.35 + energy * 0.35
            chord = bars[0].chord_pitches or [root, root + 4, root + 7]
            motif = create_motif(scale, chord, energy, density, rng)
            is_outro = section_id == "outro" or section_id == outro_id

            for bar_index, bar in enumerate(bars):
                transform = self._pick_transform(section_id, energy, is_outro, bar_index, rng)
                transformed = transform_motif(motif, transform, rng)
                velocity = int(62 + energy * 36)
                context = GenerationContext(
                    start_beat=(bar.bar_index - 1) * bpb,
                    root_pitch=root,
                    velocity=velocity,
                    channel=channel,
                    pitch_min=_MIN_PITCH,
                    pitch_max=_MAX_PITCH,
                    scale_degrees=scale_degrees,
                )
                notes.extend(motif_to_note_events(transformed, context))
        return notes

    @staticmethod
    def _pick_transform(
        section_id: str,
        energy: float,
        is_outro: bool,
        bar_index: int,
        rng: random.Random,
    ) -> str:
        if is_outro:
            choices = ["simplify", "repeat", "simplify", "rhythm_variation"]
        elif section_id == "chorus" or energy >= 0.7:
            choices = ["intensify", "sequence_up", "intensify", "rhythm_variation"]
        elif section_id == "verse":
            choices = ["repeat", "ornament", "repeat", "rhythm_variation"]
        else:
            choices = ["repeat", "simplify", "repeat", "ornament"]
        if bar_index < len(choices):
            return choices[bar_index]
        return rng.choice(choices)
