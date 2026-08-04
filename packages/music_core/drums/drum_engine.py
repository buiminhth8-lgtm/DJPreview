"""鼓组引擎：GM 标准鼓组，channel 9。"""

from __future__ import annotations

import random

from packages.music_core.composer.events import NoteEvent, beats_per_bar, section_energy
from packages.music_core.harmony.harmony_engine import BarHarmony
from packages.music_core.midi.midi_constants import DRUM_CHANNEL
from packages.music_core.rhythm.rhythm_patterns import DRUM_PATTERNS
from services.api.schemas.music_spec import MusicSpec

_DRUM_BASE_VELOCITY = {
    36: 100,   # kick
    38: 100,   # snare
    42: 70,    # closed hi-hat
    46: 75,    # open hi-hat
    49: 95,    # crash
    51: 70,    # ride
}


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


class DrumEngine:
    """生成 GM 鼓组 NoteEvent 列表（MIDI channel 9）。"""

    def _pick_template(self, music_spec: MusicSpec) -> str:
        style = " ".join(music_spec.style).lower()
        mood = " ".join(music_spec.mood).lower()
        if any(k in style for k in ("cinematic", "ambient")) or any(k in mood for k in ("忧郁", "空灵", "悲伤", "雨夜")):
            return "cinematic"
        if "lo-fi" in style or "lofi" in style:
            return "lo-fi"
        if "rock" in style:
            return "rock"
        if "electronic" in style or "edm" in style:
            return "electronic"
        return "pop"

    def generate(
        self,
        music_spec: MusicSpec,
        bar_harmony: list[BarHarmony],
        channel: int = DRUM_CHANNEL,
    ) -> list[NoteEvent]:
        rng = random.Random(music_spec.seed + 11)
        template = self._pick_template(music_spec)
        pattern = DRUM_PATTERNS[template]()
        bpb = beats_per_bar(music_spec)
        notes: list[NoteEvent] = []
        outro_id = music_spec.form[-1].id if music_spec.form else None

        for bar in bar_harmony:
            energy = section_energy(music_spec, bar.section_id)
            is_outro = bar.section_id == "outro" or (outro_id is not None and bar.section_id == outro_id)
            bar_start = (bar.bar_index - 1) * bpb

            for drum_note, hits in pattern.items():
                for beat, duration, vel_scale in hits:
                    if is_outro and drum_note != 36:
                        continue  # outro 只保留低频鼓点
                    base = _DRUM_BASE_VELOCITY.get(drum_note, 80)
                    velocity = _clamp(int(base * vel_scale * (0.75 + energy * 0.35)), 1, 127)
                    notes.append(
                        NoteEvent(
                            pitch=drum_note,
                            start_beat=round(bar_start + beat, 3),
                            duration_beats=round(duration, 3),
                            velocity=velocity,
                            channel=channel,
                            is_drum=True,
                        )
                    )

            # energy 高时补充十六分踩镲，增强律动
            if energy >= 0.75:
                for e in (0.25, 1.25, 2.25, 3.25):
                    notes.append(
                        NoteEvent(
                            pitch=42,
                            start_beat=round(bar_start + e, 3),
                            duration_beats=0.1,
                            velocity=_clamp(int(55 + energy * 25), 1, 127),
                            channel=channel,
                            is_drum=True,
                        )
                    )
        return notes
