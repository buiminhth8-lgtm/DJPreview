"""Build authoritative, bounded T35 AI MIDI edit Context without calling an LLM."""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from typing import Any

from packages.music_core.midi_editing.models import MidiEditScope
from packages.music_core.midi_editing.scope import (
    MidiEditScopeError,
    scope_fingerprint,
    select_scoped_notes,
)
from services.api.schemas.ai_midi_edit import (
    AiMidiChordContext,
    AiMidiEditContext,
    AiMidiSectionContext,
    GenerateAiMidiEditProposalRequest,
)
from services.api.schemas.midi_editor import (
    MidiEditorDocument,
    MidiEditorNote,
    MidiEditorTrack,
)
from services.api.schemas.music_spec import MusicSpec

MAX_EXACT_PLANNER_NOTES = 128
MAX_PLANNER_CHORDS = 64
MAX_PLANNER_PAYLOAD_BYTES = 64 * 1024


class AiMidiEditContextError(ValueError):
    """The requested Context cannot be built from authoritative project data."""


def _ticks_per_bar(ppq: int, meter: tuple[int, int]) -> int:
    numerator, denominator = meter
    if numerator <= 0 or denominator <= 0:
        raise AiMidiEditContextError("time signature 必须为正数")
    denominator_beat = math.floor((ppq * 4) / denominator + 0.5)
    return max(1, numerator) * max(1, denominator_beat)


def _document_total_ticks(
    document: MidiEditorDocument,
    spec: MusicSpec,
    draft_notes: Sequence[MidiEditorNote],
) -> int:
    per_bar = _ticks_per_bar(document.ppq, document.time_signature)
    declared = math.ceil(max(document.total_bars, spec.length.bars, 0) * per_bar)
    note_end = max(
        (
            note.start_tick + note.duration_tick
            for track in document.tracks
            for note in track.notes
        ),
        default=0,
    )
    draft_end = max(
        (note.start_tick + note.duration_tick for note in draft_notes),
        default=0,
    )
    return max(declared, note_end, draft_end)


def _find_track(document: MidiEditorDocument, track_id: str) -> MidiEditorTrack:
    track = next((item for item in document.tracks if item.id == track_id), None)
    if track is None:
        raise AiMidiEditContextError(f"当前 MIDI 不存在 track_id：{track_id}")
    return track


def _section_contexts(
    spec: MusicSpec,
    document: MidiEditorDocument,
) -> list[AiMidiSectionContext]:
    per_bar = _ticks_per_bar(document.ppq, document.time_signature)
    return sorted(
        [
            AiMidiSectionContext(
                id=section.id,
                name=section.name,
                start_bar=section.start_bar,
                bars=section.bars,
                start_tick=(section.start_bar - 1) * per_bar,
                end_tick=(section.start_bar - 1 + section.bars) * per_bar,
                energy=section.energy,
            )
            for section in spec.form
        ],
        key=lambda item: (item.start_tick, item.id),
    )


def _scope_time_window(
    scope: MidiEditScope,
    total_ticks: int,
    notes: Sequence[MidiEditorNote],
) -> tuple[int, int]:
    if scope.type in ("section", "tick_range"):
        return scope.start_tick, scope.end_tick
    if scope.type == "selected_notes" and notes:
        return (
            min(note.start_tick for note in notes),
            max(note.start_tick + note.duration_tick for note in notes),
        )
    return 0, total_ticks


def _chord_contexts(
    spec: MusicSpec,
    document: MidiEditorDocument,
    sections: Sequence[AiMidiSectionContext],
    window: tuple[int, int],
) -> list[AiMidiChordContext]:
    per_bar = _ticks_per_bar(document.ppq, document.time_signature)
    by_id = {section.id: section for section in sections}
    start, end = window
    result: list[AiMidiChordContext] = []
    for harmony in spec.harmony:
        section = by_id.get(harmony.section)
        progression = [symbol.strip() for symbol in harmony.progression if symbol.strip()]
        if section is None or not progression:
            continue
        for offset in range(section.bars):
            chord_start = section.start_tick + offset * per_bar
            chord_end = chord_start + per_bar
            if chord_end <= start or chord_start >= end:
                continue
            result.append(
                AiMidiChordContext(
                    section_id=section.id,
                    symbol=progression[offset % len(progression)],
                    bar=section.start_bar + offset,
                    start_tick=chord_start,
                    end_tick=chord_end,
                )
            )
    return sorted(
        result,
        key=lambda item: (item.start_tick, item.section_id, item.symbol),
    )[:MAX_PLANNER_CHORDS]


def build_ai_midi_edit_context(
    *,
    song_id: str,
    current_version_id: str | None,
    request: GenerateAiMidiEditProposalRequest,
    music_spec: MusicSpec,
    document: MidiEditorDocument,
) -> AiMidiEditContext:
    """Combine scoped session Draft with authoritative project metadata."""
    if document.song_id != song_id:
        raise AiMidiEditContextError(
            f"MIDI document song_id 不匹配（expected={song_id}, actual={document.song_id}）"
        )
    if document.version_id != current_version_id:
        raise AiMidiEditContextError("MIDI document version 与 current version 不一致")
    if request.base_version_id != current_version_id:
        raise AiMidiEditContextError("base_version_id 已过期")

    scope = request.scope
    track = _find_track(document, scope.track_id)
    total_ticks = _document_total_ticks(document, music_spec, request.draft_notes)
    if scope.type in ("section", "tick_range") and scope.end_tick > total_ticks:
        raise MidiEditScopeError(
            f"Scope end_tick={scope.end_tick} 超出 total_ticks={total_ticks}"
        )

    sections = _section_contexts(music_spec, document)
    selected_section: AiMidiSectionContext | None = None
    if scope.type == "section":
        selected_section = next(
            (section for section in sections if section.id == scope.section_id),
            None,
        )
        if selected_section is None:
            raise MidiEditScopeError(f"MusicSpec 不存在 section_id：{scope.section_id}")
        if (
            selected_section.start_tick != scope.start_tick
            or selected_section.end_tick != scope.end_tick
        ):
            raise MidiEditScopeError(
                "section tick 边界与当前 MusicSpec/PPQ/time signature 不一致"
            )

    scoped_notes = select_scoped_notes(scope, request.draft_notes)
    spec_track = next(
        (candidate for candidate in music_spec.tracks if candidate.id == track.id),
        None,
    )
    role = spec_track.role if spec_track is not None else track.role
    instrument = spec_track.instrument if spec_track is not None else track.instrument
    window = _scope_time_window(scope, total_ticks, scoped_notes)
    chords = _chord_contexts(music_spec, document, sections, window)
    if selected_section is None and scope.type == "tick_range":
        intersecting = [
            section
            for section in sections
            if section.end_tick > scope.start_tick and section.start_tick < scope.end_tick
        ]
        selected_section = intersecting[0] if len(intersecting) == 1 else None

    channels = sorted({note.channel for note in scoped_notes}) or [track.channel]
    return AiMidiEditContext(
        song_id=song_id,
        base_version_id=request.base_version_id,
        editor_session_id=request.editor_session_id,
        draft_revision=request.draft_revision,
        scope_revision=request.scope_revision,
        scope_fingerprint=scope_fingerprint(scope),
        scope=scope,
        track_id=track.id,
        track_role=role,
        instrument=instrument,
        is_drum=track.is_drum,
        channel_summary=channels,
        ppq=document.ppq,
        tempo_bpm=document.bpm,
        time_signature=document.time_signature,
        total_ticks=total_ticks,
        scoped_notes=scoped_notes,
        key=music_spec.tonality.key,
        mode=music_spec.tonality.mode,
        scale=music_spec.tonality.scale,
        section=selected_section,
        chords=chords,
    )


def _note_json(note: MidiEditorNote) -> dict[str, int]:
    return {
        "pitch": note.pitch,
        "startTick": note.start_tick,
        "durationTick": note.duration_tick,
        "velocity": note.velocity,
        "channel": note.channel,
    }


def _uniform_sample(notes: Sequence[MidiEditorNote], limit: int) -> list[MidiEditorNote]:
    if len(notes) <= limit:
        return list(notes)
    if limit <= 1:
        return [notes[0]]
    indexes = [
        math.floor(index * (len(notes) - 1) / (limit - 1) + 0.5)
        for index in range(limit)
    ]
    return [notes[index] for index in indexes]


def _note_statistics(notes: Sequence[MidiEditorNote]) -> dict[str, Any]:
    if not notes:
        return {
            "count": 0,
            "pitchRange": None,
            "startTickRange": None,
            "velocityRange": None,
            "durationTickRange": None,
        }
    pitches = [note.pitch for note in notes]
    starts = [note.start_tick for note in notes]
    velocities = [note.velocity for note in notes]
    durations = [note.duration_tick for note in notes]
    return {
        "count": len(notes),
        "pitchRange": [min(pitches), max(pitches)],
        "startTickRange": [min(starts), max(starts)],
        "velocityRange": [min(velocities), max(velocities)],
        "durationTickRange": [min(durations), max(durations)],
    }


def build_planner_payload(
    context: AiMidiEditContext,
    *,
    instruction: str,
) -> dict[str, Any]:
    """Create a deterministic, token-bounded payload. This function never calls an LLM."""
    notes = context.scoped_notes
    exact = len(notes) <= MAX_EXACT_PLANNER_NOTES
    sampled = notes if exact else _uniform_sample(notes, MAX_EXACT_PLANNER_NOTES)
    payload: dict[str, Any] = {
        "instruction": instruction.strip(),
        "scope": {
            "type": context.scope.type,
            "noteCount": len(notes),
            **(
                {
                    "startTick": context.scope.start_tick,
                    "endTick": context.scope.end_tick,
                }
                if context.scope.type in ("section", "tick_range")
                else {}
            ),
        },
        "track": {
            "role": context.track_role,
            "instrument": context.instrument,
            "isDrum": context.is_drum,
            "channels": context.channel_summary,
        },
        "time": {
            "ppq": context.ppq,
            "tempoBpm": context.tempo_bpm,
            "timeSignature": list(context.time_signature),
            "totalTicks": context.total_ticks,
        },
        "tonality": {
            "key": context.key,
            "mode": context.mode,
            "scale": context.scale,
        },
        "section": context.section.model_dump(mode="json") if context.section else None,
        "chords": [chord.model_dump(mode="json") for chord in context.chords],
        "notes": {
            "complete": exact,
            "statistics": _note_statistics(notes),
            "items": [_note_json(note) for note in sampled],
        },
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_PLANNER_PAYLOAD_BYTES:
        raise AiMidiEditContextError(
            f"planner payload 超过 {MAX_PLANNER_PAYLOAD_BYTES} bytes"
        )
    return payload
