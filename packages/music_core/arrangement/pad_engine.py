"""Pad 引擎（T22）：长音和弦铺底 + 平滑 voice leading + 段落层次。"""

from __future__ import annotations

import random

from packages.music_core.composer.events import NoteEvent, beats_per_bar, section_energy
from packages.music_core.composer.voice_leading import smooth_voice_leading
from packages.music_core.harmony.harmony_engine import BarHarmony
from services.api.schemas.music_spec import MusicSpec, TrackSpec


def _profile(section_id: str, energy: float) -> dict:
    """段落 pad 轮廓：voices / register / velocity / duration。"""
    sid = (section_id or "").strip().lower()
    e = max(0.0, min(1.0, energy))
    if sid in ("intro", "前奏"):
        return {"voices": 2, "register": (48, 64), "velocity": int(40 + e * 10), "duration": 3.8}
    if sid in ("verse", "主歌"):
        return {"voices": 3, "register": (48, 67), "velocity": int(45 + e * 14), "duration": 3.8}
    if sid in ("pre_chorus", "prechorus", "前副歌"):
        return {"voices": 4, "register": (50, 72), "velocity": int(58 + e * 18), "duration": 3.5, "build": True}
    if sid in ("chorus", "副歌"):
        return {"voices": 4, "register": (52, 76), "velocity": int(65 + e * 20), "duration": 3.5, "lift": True}
    if sid in ("bridge", "桥段"):
        return {"voices": 3, "register": (48, 67), "velocity": int(52 + e * 14), "duration": 3.8, "contrast": True}
    if sid in ("outro", "尾奏"):
        return {"voices": 2, "register": (48, 64), "velocity": int(42 + e * 14), "duration": 4.0, "thin": True}
    return {"voices": 3, "register": (48, 72), "velocity": int(50 + e * 16), "duration": 3.5}


class PadEngine:
    """生成 pad track NoteEvent（长音和弦，音区高于 bass、低于/错开 melody 核心区）。"""

    def generate(
        self,
        music_spec: MusicSpec,
        bar_harmony: list[BarHarmony],
        track: TrackSpec,
        channel: int = 3,
    ) -> list[NoteEvent]:
        rng = random.Random(music_spec.seed + 17)
        bpb = beats_per_bar(music_spec)
        sections: dict[str, list[BarHarmony]] = {}
        for bar in bar_harmony:
            sections.setdefault(bar.section_id, []).append(bar)

        notes: list[NoteEvent] = []
        for section_id, bars in sections.items():
            if track.enabled_sections and section_id not in track.enabled_sections:
                continue
            energy = section_energy(music_spec, section_id)
            profile = _profile(section_id, energy)
            symbols = [bar.chord_symbol for bar in bars]
            voicings = smooth_voice_leading(
                symbols,
                register=profile["register"],
                voice_count=profile["voices"],
            )
            for bar, voicing in zip(bars, voicings):
                bar_start = (bar.bar_index - 1) * bpb
                velocity_base = profile["velocity"]
                for i, pitch in enumerate(voicing):
                    velocity = velocity_base + (4 if i == 0 else 0) + (5 if profile.get("lift") else 0)
                    notes.append(
                        NoteEvent(
                            pitch=pitch,
                            start_beat=round(bar_start, 3),
                            duration_beats=round(profile["duration"], 3),
                            velocity=max(1, min(127, velocity)),
                            channel=channel,
                        )
                    )
                # chorus 高八度 layer
                if profile.get("lift"):
                    top = max(voicing)
                    if top + 12 <= 84:
                        notes.append(
                            NoteEvent(
                                pitch=top + 12,
                                start_beat=round(bar_start, 3),
                                duration_beats=round(profile["duration"], 3),
                                velocity=max(1, min(127, velocity_base + 6)),
                                channel=channel,
                            )
                        )
                # pre_chorus build：小节中段补一次高音
                if profile.get("build") and voicing:
                    top = max(voicing)
                    notes.append(
                        NoteEvent(
                            pitch=min(top + 7, profile["register"][1] + 7),
                            start_beat=round(bar_start + 2.0, 3),
                            duration_beats=1.4,
                            velocity=max(1, min(127, velocity_base + 6)),
                            channel=channel,
                        )
                    )
        return notes
