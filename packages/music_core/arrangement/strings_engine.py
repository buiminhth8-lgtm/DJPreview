"""弦乐引擎（T22）：sustained / light rhythmic / ostinato strings + 段落层次。"""

from __future__ import annotations

import random

from packages.music_core.composer.events import NoteEvent, beats_per_bar, section_energy
from packages.music_core.composer.voice_leading import smooth_voice_leading
from packages.music_core.harmony.harmony_engine import BarHarmony
from services.api.schemas.music_spec import MusicSpec, TrackSpec


def _profile(section_id: str, energy: float, style: str) -> dict:
    """段落弦乐轮廓：voices / register / velocity / duration / mode。"""
    sid = (section_id or "").strip().lower()
    e = max(0.0, min(1.0, energy))
    if sid in ("intro", "前奏"):
        return {"voices": 2, "register": (55, 72), "velocity": 48, "duration": 3.5, "mode": "sustain", "skip": False}
    if sid in ("verse", "主歌"):
        return {"voices": 3, "register": (55, 76), "velocity": int(55 + e * 12), "duration": 3.5, "mode": "sustain"}
    if sid in ("pre_chorus", "prechorus", "前副歌"):
        return {"voices": 3, "register": (57, 79), "velocity": int(65 + e * 18), "duration": 2.0, "mode": "sustain", "build": True}
    if sid in ("chorus", "副歌"):
        return {"voices": 4, "register": (60, 84), "velocity": int(78 + e * 22), "duration": 3.0, "mode": "sustain", "lift": True}
    if sid in ("bridge", "桥段"):
        return {"voices": 3, "register": (55, 76), "velocity": int(60 + e * 14), "duration": 3.5, "mode": "sustain", "contrast": True}
    if sid in ("outro", "尾奏"):
        return {"voices": 2, "register": (55, 72), "velocity": int(45 + e * 18), "duration": 4.0, "mode": "sustain", "thin": True}
    return {"voices": 3, "register": (55, 79), "velocity": int(60 + e * 16), "duration": 3.0, "mode": "sustain"}


def _style_mode(style: str) -> str:
    if "cinematic" in style or "ambient" in style:
        return "cinematic"
    if "rock" in style:
        return "rock"
    if "lo-fi" in style or "lofi" in style or "hiphop" in style:
        return "lo-fi"
    if "chinese" in style:
        return "chinese"
    return "pop"


class StringsEngine:
    """生成 strings track NoteEvent（sustained / light stab / 可选 ostinato）。"""

    def generate(
        self,
        music_spec: MusicSpec,
        bar_harmony: list[BarHarmony],
        track: TrackSpec,
        channel: int = 3,
    ) -> list[NoteEvent]:
        rng = random.Random(music_spec.seed + 13)
        style = _style_mode(" ".join(music_spec.style).lower())
        bpb = beats_per_bar(music_spec)
        sections: dict[str, list[BarHarmony]] = {}
        for bar in bar_harmony:
            sections.setdefault(bar.section_id, []).append(bar)

        notes: list[NoteEvent] = []
        for section_id, bars in sections.items():
            if track.enabled_sections and section_id not in track.enabled_sections:
                continue
            energy = section_energy(music_spec, section_id)
            profile = _profile(section_id, energy, style)
            if profile.get("skip") or (style == "lo-fi" and section_id in ("verse", "主歌")):
                continue
            symbols = [bar.chord_symbol for bar in bars]
            voicings = smooth_voice_leading(
                symbols,
                register=profile["register"],
                voice_count=profile["voices"],
            )
            for bar, voicing in zip(bars, voicings):
                bar_start = (bar.bar_index - 1) * bpb
                duration = profile["duration"]
                velocity_base = profile["velocity"]
                mode = profile.get("mode", "sustain")
                if mode == "sustain":
                    for i, pitch in enumerate(voicing):
                        velocity = velocity_base + (4 if i == 0 else 0) + (6 if profile.get("lift") else 0)
                        notes.append(
                            NoteEvent(
                                pitch=pitch,
                                start_beat=round(bar_start, 3),
                                duration_beats=round(duration, 3),
                                velocity=max(1, min(127, velocity)),
                                channel=channel,
                            )
                        )
                else:
                    # 短促 stab（rock / pop chorus 轻节奏层）
                    for beat in (0.0, 2.0):
                        for pitch in voicing:
                            notes.append(
                                NoteEvent(
                                    pitch=pitch,
                                    start_beat=round(bar_start + beat, 3),
                                    duration_beats=0.8,
                                    velocity=max(1, min(127, velocity_base + 4)),
                                    channel=channel,
                                )
                            )
                # pre_chorus build：上行小句
                if profile.get("build") and voicing:
                    top = max(voicing)
                    for step, beat in enumerate((1.0, 2.5)):
                        pitch = min(top + 2 + step * 2, profile["register"][1])
                        notes.append(
                            NoteEvent(
                                pitch=pitch,
                                start_beat=round(bar_start + beat, 3),
                                duration_beats=0.7,
                                velocity=max(1, min(127, velocity_base + 6 + step * 4)),
                                channel=channel,
                            )
                        )
                # cinematic ostinato（张力段落）
                if style == "cinematic" and profile.get("build") and voicing:
                    base_pitch = voicing[0]
                    for i in range(4):
                        notes.append(
                            NoteEvent(
                                pitch=base_pitch,
                                start_beat=round(bar_start + 0.5 + i * 0.5, 3),
                                duration_beats=0.35,
                                velocity=max(1, min(127, velocity_base - 8)),
                                channel=channel,
                            )
                        )
        return notes
