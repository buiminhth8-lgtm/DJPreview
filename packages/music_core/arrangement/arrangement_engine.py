"""伴奏引擎：为 harmony / pad / strings 轨道生成伴奏。"""

from __future__ import annotations

from packages.music_core.composer.events import NoteEvent, beats_per_bar, section_energy
from packages.music_core.harmony.harmony_engine import BarHarmony
from packages.music_core.rhythm import rhythm_patterns
from services.api.schemas.music_spec import MusicSpec, TrackSpec

_AUTO_ARPEGGIO_KEYWORDS = ("cinematic", "ambient", "忧郁", "空灵", "悲伤", "雨夜")
_AUTO_BLOCK_KEYWORDS = ("pop", "明亮", "欢快")


def _register_shift(register: str | None) -> int:
    """按音区描述做八度平移。"""
    if not register:
        return 0
    reg = register.lower()
    if "low" in reg:
        return -12
    if "high" in reg:
        return 12
    return 0


def _pick_harmony_pattern(track: TrackSpec, music_spec: MusicSpec) -> str:
    """选择伴奏织体：优先 TrackSpec.pattern，否则按风格/情绪自动选择。"""
    if track.pattern:
        candidate = track.pattern.strip().lower()
        if candidate in rhythm_patterns.PITCHED_PATTERNS:
            return candidate
    style_mood = " ".join(music_spec.style + music_spec.mood).lower()
    if any(keyword in style_mood for keyword in _AUTO_ARPEGGIO_KEYWORDS):
        return "arpeggio"
    if any(keyword in style_mood for keyword in _AUTO_BLOCK_KEYWORDS):
        return "broken_chords"
    return "block_chords"


class ArrangementEngine:
    """为 harmony / pad / strings 轨道生成伴奏 NoteEvent 列表。"""

    def generate(
        self,
        music_spec: MusicSpec,
        bar_harmony: list[BarHarmony],
        track: TrackSpec,
        channel: int = 1,
    ) -> list[NoteEvent]:
        role = track.role or ""
        if role in ("pad", "strings"):
            pattern_name = "sustained_pad"
        else:
            pattern_name = _pick_harmony_pattern(track, music_spec)
        pattern = rhythm_patterns.PITCHED_PATTERNS[pattern_name]()
        bpb = beats_per_bar(music_spec)
        shift = _register_shift(track.register)
        notes: list[NoteEvent] = []

        for bar in bar_harmony:
            if track.enabled_sections and bar.section_id not in track.enabled_sections:
                continue
            energy = section_energy(music_spec, bar.section_id)
            velocity = int(45 + energy * 50)
            bar_start = (bar.bar_index - 1) * bpb
            chord = bar.chord_pitches or [60, 64, 67]

            for hit in pattern:
                beat, duration, vel_scale = hit
                if pattern_name == "arpeggio":
                    idx = int(round(beat)) % len(chord)
                    notes.append(
                        self._make_note(chord[idx] + shift, bar_start + beat, duration, velocity, vel_scale, channel)
                    )
                elif pattern_name == "broken_chords":
                    if int(beat * 2) % 2 == 0:
                        pitch = chord[0] + shift
                    else:
                        pitch = (chord[1] if len(chord) > 1 else chord[0]) + 12 + shift
                    notes.append(self._make_note(pitch, bar_start + beat, duration, velocity, vel_scale, channel))
                else:
                    # block_chords / sustained_pad / long_chords：整组和弦
                    for pitch in chord:
                        notes.append(self._make_note(pitch + shift, bar_start + beat, duration, velocity, vel_scale, channel))
        return notes

    @staticmethod
    def _make_note(
        pitch: int,
        start: float,
        duration: float,
        velocity: int,
        vel_scale: float,
        channel: int,
    ) -> NoteEvent:
        pitch = max(0, min(127, int(pitch)))
        vel = max(1, min(127, int(velocity * vel_scale)))
        return NoteEvent(
            pitch=pitch,
            start_beat=round(start, 3),
            duration_beats=round(duration, 3),
            velocity=vel,
            channel=channel,
        )
