"""参考 MIDI 分析：只提取结构/密度/音域/节奏/能量等高层特征，不复制旋律。"""

from __future__ import annotations

from pathlib import Path

from packages.music_core.analysis.midi_parser import parse_midi_to_notes
from packages.music_core.reference.reference_models import ReferenceMidiAnalysis

_ROLE_INSTRUMENTS = {
    "drums": "drums",
    "bass": "bass",
    "melody": "lead_synth",
    "harmony": "piano",
    "pad": "strings",
}


def _max_polyphony(notes) -> int:
    events = sorted(
        [(n.start_beat, 1) for n in notes] + [(n.start_beat + n.duration_beats, -1) for n in notes],
        key=lambda x: (x[0], x[1]),
    )
    current = 0
    peak = 0
    for _, delta in events:
        current += delta
        peak = max(peak, current)
    return peak


def _guess_role(track, has_drums: bool) -> str:
    if track.channel == 9 or has_drums and track.channel == 9:
        return "drums"
    avg_pitch = sum(n.pitch for n in track.notes) / len(track.notes) if track.notes else 60
    polyphony = _max_polyphony(track.notes)
    if avg_pitch < 48:
        return "bass"
    if polyphony >= 3:
        return "pad" if avg_pitch < 70 else "harmony"
    if avg_pitch >= 58:
        return "melody"
    return "harmony"


def _suggest_tags(bpm: int | None, has_drums: bool, notes_per_bar: float) -> list[str]:
    tags: list[str] = []
    if bpm is None:
        pass
    elif bpm <= 80:
        tags.append("slow")
        tags.append("ballad")
    elif bpm <= 120:
        tags.append("pop")
        tags.append("lo-fi")
    else:
        tags.append("fast")
        tags.append("rock")
    if has_drums:
        tags.append("rhythmic")
    if notes_per_bar < 6:
        tags.append("ambient")
    elif notes_per_bar > 30:
        tags.append("dense")
    return tags[:5]


def analyze_reference_midi(midi_path: str | Path) -> ReferenceMidiAnalysis:
    """分析参考 MIDI，输出高层特征。"""
    path = Path(midi_path)
    parsed = parse_midi_to_notes(path)
    all_notes = [n for t in parsed.tracks for n in t.notes]
    note_count = len(all_notes)
    track_count = len(parsed.tracks)
    bpm = parsed.bpm
    estimated_bars = parsed.total_bars

    pitches = [n.pitch for n in all_notes]
    pitch_range = {
        "min": min(pitches) if pitches else None,
        "max": max(pitches) if pitches else None,
    }
    notes_per_bar = round(note_count / estimated_bars, 2) if estimated_bars else 0.0
    avg_velocity = round(sum(n.velocity for n in all_notes) / note_count) if note_count else 0
    density = {
        "notes_per_bar": notes_per_bar,
        "avg_velocity": avg_velocity,
        "max_velocity": max((n.velocity for n in all_notes), default=0),
    }
    has_drums = any(n.is_drum for n in all_notes)
    avg_duration = round(sum(n.duration_beats for n in all_notes) / note_count, 3) if note_count else 0.0
    rhythm_profile = {"has_drums": has_drums, "avg_duration_beats": avg_duration}

    # energy curve：每 4 小节一段
    energy_curve: list[dict] = []
    if estimated_bars > 0:
        per_bar: dict[int, list] = {}
        for n in all_notes:
            bar = int(n.start_beat // 4) + 1
            per_bar.setdefault(bar, []).append(n)
        max_count = max((len(v) for v in per_bar.values()), default=1)
        segments: dict[int, list] = {}
        for bar, notes in per_bar.items():
            seg = (bar - 1) // 4
            segments.setdefault(seg, []).extend(notes)
        for seg in sorted(segments):
            notes = segments[seg]
            count = len(notes)
            avg_vel = sum(n.velocity for n in notes) / len(notes)
            energy = min(1.0, (count / max_count) * 0.7 + (avg_vel / 127.0) * 0.3)
            energy_curve.append(
                {
                    "segment_index": seg,
                    "start_bar": seg * 4 + 1,
                    "note_count": count,
                    "energy": round(energy, 3),
                }
            )

    track_summaries: list[dict] = []
    possible_roles: list[str] = []
    for track in parsed.tracks:
        role = _guess_role(track, has_drums)
        if role not in possible_roles:
            possible_roles.append(role)
        track_summaries.append(
            {
                "track_index": track.track_index,
                "track_name": track.track_name,
                "channel": track.channel,
                "role_guess": role,
                "note_count": track.note_count,
                "min_pitch": track.min_pitch,
                "max_pitch": track.max_pitch,
            }
        )

    suggested_tags = _suggest_tags(bpm, has_drums, notes_per_bar)
    suggested_tempo_range = (max(40, bpm - 25), min(220, bpm + 25)) if bpm else None
    suggested_tracks = [
        {"role": role, "instrument": _ROLE_INSTRUMENTS.get(role, "piano")}
        for role in possible_roles
    ]
    warnings = (
        ["未检测到 BPM，使用默认值"] if bpm is None else []
    )

    return ReferenceMidiAnalysis(
        file_name=path.name,
        ticks_per_beat=parsed.ticks_per_beat,
        bpm=bpm,
        estimated_bars=estimated_bars,
        track_count=track_count,
        note_count=note_count,
        pitch_range=pitch_range,
        density=density,
        rhythm_profile=rhythm_profile,
        energy_curve=energy_curve,
        track_summaries=track_summaries,
        possible_roles=possible_roles,
        suggested_style_tags=suggested_tags,
        suggested_tempo_range=suggested_tempo_range,
        suggested_tracks=suggested_tracks,
        warnings=warnings,
    )
