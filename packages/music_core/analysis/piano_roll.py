"""Piano Roll 数据构建：ParsedMidi → 前端友好 JSON。"""

from __future__ import annotations

from packages.music_core.analysis.midi_parser import ParsedMidi
from services.api.schemas.music_spec import MusicSpec


def _role_for_track(track_name: str | None, music_spec: MusicSpec | None) -> str | None:
    if not track_name or music_spec is None:
        return None
    for track in music_spec.tracks:
        if track.id == track_name or track_name.startswith(f"{track.id}_"):
            return track.role
    return None


def build_piano_roll_data(
    parsed_midi: ParsedMidi,
    music_spec: MusicSpec | None = None,
    *,
    max_notes: int = 5000,
    track_id: str | None = None,
) -> dict:
    """返回前端友好的钢琴卷帘 JSON；音符过多时截断并标记 truncated。"""
    beats_per_bar = music_spec.meter.numerator if music_spec and music_spec.meter.denominator == 4 else 4
    sections = []
    if music_spec:
        sections = [
            {
                "id": s.id,
                "name": s.name,
                "start_bar": s.start_bar,
                "bars": s.bars,
                "energy": s.energy,
            }
            for s in music_spec.form
        ]

    tracks_out: list[dict] = []
    total_notes = 0
    truncated = False
    for parsed_track in parsed_midi.tracks:
        role = _role_for_track(parsed_track.track_name, music_spec)
        if track_id and role != track_id and parsed_track.track_name != track_id:
            continue
        notes_out = []
        for note in parsed_track.notes:
            if total_notes >= max_notes:
                truncated = True
                break
            notes_out.append(
                {
                    "pitch": note.pitch,
                    "pitch_name": note.pitch_name,
                    "start_beat": note.start_beat,
                    "duration_beats": note.duration_beats,
                    "velocity": note.velocity,
                    "is_drum": note.is_drum,
                }
            )
            total_notes += 1
        tracks_out.append(
            {
                "track_index": parsed_track.track_index,
                "track_name": parsed_track.track_name,
                "role": role,
                "min_pitch": parsed_track.min_pitch,
                "max_pitch": parsed_track.max_pitch,
                "notes": notes_out,
            }
        )
        if truncated:
            break

    return {
        "ticks_per_beat": parsed_midi.ticks_per_beat,
        "bpm": parsed_midi.bpm,
        "beats_per_bar": beats_per_bar,
        "total_bars": parsed_midi.total_bars,
        "total_notes": total_notes,
        "truncated": truncated,
        "sections": sections,
        "tracks": tracks_out,
    }
