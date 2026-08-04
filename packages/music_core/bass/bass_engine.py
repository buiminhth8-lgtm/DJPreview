"""贝斯引擎（T21）：风格 groove + 段落强度 + root/fifth/octave + passing/approach + kick 对齐。"""

from __future__ import annotations

import random

from packages.music_core.composer.bass_models import BassNote
from packages.music_core.composer.bass_patterns import (
    BASS_GROOVES,
    BASS_MAX,
    BASS_MIN,
    bass_style_swing,
    build_approach_note,
    choose_passing_tone,
    get_chord_root_pitch,
    implied_kick_positions,
)
from packages.music_core.composer.events import NoteEvent, beats_per_bar, section_energy
from packages.music_core.harmony.harmony_engine import BarHarmony
from packages.music_core.theory.rhythm import apply_swing
from packages.music_core.theory.scales import get_scale_pitches
from services.api.schemas.music_spec import MusicSpec


def _clamp(value: int, low: int = 1, high: int = 127) -> int:
    return max(low, min(high, value))


def extract_kick_positions(
    drum_events: list[NoteEvent],
    section_start: float | None = None,
    section_end: float | None = None,
) -> list[float]:
    """从鼓组事件中提取 kick（note 36）时间。"""
    kicks = [n.start_beat for n in drum_events if n.pitch == 36]
    if section_start is not None:
        kicks = [k for k in kicks if k >= section_start]
    if section_end is not None:
        kicks = [k for k in kicks if k < section_end]
    return sorted(kicks)


class BassEngine:
    """生成贝斯轨道：强拍根音、风格化 groove、可选 kick 对齐。"""

    def _pick_style(self, music_spec: MusicSpec) -> str:
        style = " ".join(music_spec.style).lower()
        if "chinese" in style:
            return "chinese"
        if any(k in style for k in ("cinematic", "ambient")):
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
        channel: int = 2,
        kick_positions: list[float] | None = None,
    ) -> list[NoteEvent]:
        rng = random.Random(music_spec.seed + 7)
        template = self._pick_style(music_spec)
        swing = bass_style_swing(template)
        bpb = beats_per_bar(music_spec)
        scale = get_scale_pitches(music_spec.tonality.key, music_spec.tonality.mode or "major", 4)
        # 覆盖低音区（36-52 及相邻八度）的调内音高
        scale_pitches = set()
        for pitch in scale:
            for octave_shift in range(-3, 3):
                candidate = pitch + 12 * octave_shift
                if BASS_MIN - 12 <= candidate <= BASS_MAX + 12:
                    scale_pitches.add(candidate)

        sections: dict[str, list[BarHarmony]] = {}
        for bar in bar_harmony:
            sections.setdefault(bar.section_id, []).append(bar)

        # 全局小节序列的下一小节根音（跨段落，用于 approach note）
        next_roots: dict[int, int | None] = {}
        for i, bar in enumerate(bar_harmony):
            nxt = bar_harmony[i + 1] if i + 1 < len(bar_harmony) else None
            next_roots[bar.bar_index] = get_chord_root_pitch(nxt.chord_symbol) if nxt else None

        notes: list[NoteEvent] = []
        previous_root: int | None = None
        for section_id, bars in sections.items():
            energy = section_energy(music_spec, section_id)
            intensity = self._section_intensity(section_id, energy)
            for bar_index, bar in enumerate(bars):
                bar_start = (bar.bar_index - 1) * bpb
                root = get_chord_root_pitch(bar.chord_symbol, music_spec.tonality.key)
                fifth = root + 7 if root + 7 <= BASS_MAX else root - 5
                octave = root + 12 if root + 12 <= BASS_MAX else root
                groove = BASS_GROOVES[template]
                hits = list(groove(root, fifth, octave, intensity, rng))

                # 弱拍 passing tone（小节中段，调内）
                if intensity >= 0.7 and len(hits) >= 2 and previous_root is not None:
                    passing = choose_passing_tone(previous_root, root, scale_pitches)
                    if passing is not None and BASS_MIN <= passing <= BASS_MAX:
                        hits.append(
                            BassNote(1.5, 0.4, passing, max(1, hits[0].velocity - 15), "passing")
                        )

                # 段落末尾 approach 到下一小节根音
                next_root = next_roots.get(bar.bar_index)
                if next_root is not None and next_root != root and bar_index == len(bars) - 1:
                    approach = build_approach_note(next_root, scale_pitches)
                    if approach is not None:
                        while approach < BASS_MIN:
                            approach += 12
                    if approach is not None and BASS_MIN <= approach <= BASS_MAX:
                        hits.append(
                            BassNote(bpb - 0.25, 0.25, approach, max(1, hits[0].velocity - 10), "approach")
                        )

                # 与主要 kick 对齐
                hits = self._align_to_kicks(
                    hits,
                    bar_start,
                    bpb,
                    root,
                    scale_pitches,
                    kick_positions,
                    template,
                    rng,
                )

                # 段落力度修正 + 渲染（offbeat 应用 swing）
                velocity_boost = {
                    "intro": -12,
                    "verse": 0,
                    "pre_chorus": 6,
                    "prechorus": 6,
                    "chorus": 10,
                    "bridge": -2,
                    "outro": -10,
                }.get((section_id or "").strip().lower(), 0)

                for hit in hits:
                    time = bar_start + hit.time_beats
                    if swing > 0.5 and abs(hit.time_beats % 1.0 - 0.5) < 0.05:
                        time = apply_swing(time, swing, grid=1.0)
                    notes.append(
                        NoteEvent(
                            pitch=_clamp(hit.pitch, 0, 127),
                            start_beat=round(time, 3),
                            duration_beats=round(max(0.05, hit.duration_beats), 3),
                            velocity=_clamp(hit.velocity + velocity_boost),
                            channel=channel,
                        )
                    )
                previous_root = root
        return notes

    @staticmethod
    def _section_intensity(section_id: str, energy: float) -> float:
        base = {
            "intro": 0.25,
            "verse": 0.5,
            "pre_chorus": 0.7,
            "prechorus": 0.7,
            "chorus": 1.0,
            "bridge": 0.45,
            "outro": 0.3,
        }.get((section_id or "").strip().lower(), 0.6)
        return max(0.0, min(1.0, base + (energy - 0.5) * 0.4))

    @staticmethod
    def _align_to_kicks(
        hits: list[BassNote],
        bar_start: float,
        bpb: int,
        root: int,
        scale_pitches: set[int],
        kick_positions: list[float] | None,
        style: str,
        rng: random.Random,
    ) -> list[BassNote]:
        """在主要 kick 附近补根音，保证 bass-kick 对齐。"""
        kicks = (
            [k for k in kick_positions if bar_start <= k < bar_start + bpb]
            if kick_positions
            else [bar_start + k for k in implied_kick_positions(style)]
        )
        aligned = list(hits)
        for kick in kicks:
            within = kick - bar_start
            if any(abs(h.time_beats - within) <= 0.25 for h in hits):
                continue
            aligned.append(BassNote(round(within, 3), 0.5, root, 92, "root"))
        return aligned
