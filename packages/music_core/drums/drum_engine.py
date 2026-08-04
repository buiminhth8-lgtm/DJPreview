"""鼓组引擎（T20）：风格 groove + 段落强度 + fill + crash + swing + velocity accent。"""

from __future__ import annotations

import random

from packages.music_core.composer.drum_patterns import GM_DRUM_NOTES, build_fill
from packages.music_core.composer.drum_models import DrumHit
from packages.music_core.composer.events import NoteEvent, beats_per_bar, section_energy
from packages.music_core.composer.groove_library import (
    bridge_drum_filter,
    crash_at_section_start,
    fill_at_section_end,
    groove_for,
    intro_drum_filter,
    outro_drum_filter,
    section_intensity,
    style_swing,
)
from packages.music_core.harmony.harmony_engine import BarHarmony
from packages.music_core.midi.midi_constants import DRUM_CHANNEL
from packages.music_core.theory.rhythm import apply_swing
from services.api.schemas.music_spec import MusicSpec

_KICK = GM_DRUM_NOTES["kick"]
_CRASH = GM_DRUM_NOTES["crash"]


def _clamp(value: int, low: int = 1, high: int = 127) -> int:
    return max(low, min(high, value))


class DrumEngine:
    """生成 GM 鼓组 NoteEvent 列表（MIDI channel 9，不写 melodic program）。"""

    def _pick_template(self, music_spec: MusicSpec) -> str:
        style = " ".join(music_spec.style).lower()
        mood = " ".join(music_spec.mood).lower()
        if "chinese" in style:
            return "chinese"
        if any(k in style for k in ("cinematic", "ambient")) or any(
            k in mood for k in ("忧郁", "空灵", "悲伤", "雨夜")
        ):
            return "cinematic"
        if "lo-fi" in style or "lofi" in style or "hiphop" in style:
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
        swing = style_swing(template)
        bpb = beats_per_bar(music_spec)
        notes: list[NoteEvent] = []

        sections: dict[str, list[BarHarmony]] = {}
        for bar in bar_harmony:
            sections.setdefault(bar.section_id, []).append(bar)

        for section_id, bars in sections.items():
            energy = section_energy(music_spec, section_id)
            intensity = section_intensity(section_id, energy)
            for bar_index, bar in enumerate(bars):
                bar_start = (bar.bar_index - 1) * bpb
                hits = groove_for(template, intensity)

                # 段落特化
                sid = (section_id or "").strip().lower()
                if sid in ("intro", "前奏"):
                    hits = intro_drum_filter(hits, rng)
                elif sid in ("bridge", "桥段"):
                    hits = bridge_drum_filter(hits, rng)
                elif sid in ("outro", "尾奏"):
                    hits = outro_drum_filter(hits, rng)

                # fill：段落末尾 / chorus 每 8 小节
                if fill_at_section_end(section_id, bar_index, len(bars)):
                    hits = list(hits) + build_fill(template, rng)

                # chorus 第一小节第一拍 crash
                if crash_at_section_start(section_id, bar_index):
                    hits = list(hits) + [
                        DrumHit(time_beats=0.0, duration_beats=0.3, note=_CRASH, velocity=98, label="crash")
                    ]

                # 段落力度修正
                velocity_boost = {
                    "intro": -18,
                    "verse": 0,
                    "pre_chorus": 4,
                    "prechorus": 4,
                    "chorus": 8,
                    "bridge": -4,
                    "outro": -12,
                }.get(sid, 0)

                for hit in hits:
                    time = bar_start + hit.time_beats
                    if swing > 0.5 and abs(hit.time_beats % 1.0 - 0.5) < 0.05:
                        time = apply_swing(time, swing, grid=1.0)
                    velocity = _clamp(hit.velocity + velocity_boost)
                    notes.append(
                        NoteEvent(
                            pitch=hit.note,
                            start_beat=round(time, 3),
                            duration_beats=round(max(0.05, hit.duration_beats), 3),
                            velocity=velocity,
                            channel=channel,
                            is_drum=True,
                        )
                    )
        return notes
