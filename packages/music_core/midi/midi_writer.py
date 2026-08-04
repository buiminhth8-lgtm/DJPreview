"""MIDI Writer：CompositionResult → 标准 .mid 文件（使用 mido）。"""

from __future__ import annotations

from pathlib import Path

import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack

from packages.music_core.composer.events import CompositionResult
from packages.music_core.midi.midi_constants import DRUM_CHANNEL, GM_PROGRAMS

DEFAULT_TICKS_PER_BEAT = 480


def _resolve_program(instrument: str | None, channel: int) -> int | None:
    """乐器名 → GM program；鼓组通道不设置 program。"""
    if channel == DRUM_CHANNEL:
        return None
    if not instrument:
        return 0
    return GM_PROGRAMS.get(instrument.strip().lower(), 0)


def write_midi(composition: CompositionResult, output_path: str | Path) -> Path:
    """把 CompositionResult 写成标准 MIDI 文件，返回输出路径。"""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    tpb = composition.ticks_per_beat or DEFAULT_TICKS_PER_BEAT
    midi = MidiFile(ticks_per_beat=tpb)

    # 0 号轨道：tempo / time signature
    meta_track = MidiTrack()
    meta_track.append(MetaMessage("set_tempo", tempo=mido.bpm2tempo(composition.bpm or 120)))
    meta_track.append(
        MetaMessage(
            "time_signature",
            numerator=composition.beats_per_bar or 4,
            denominator=4,
        )
    )
    meta_track.append(MetaMessage("end_of_track"))
    midi.tracks.append(meta_track)

    for track_events in composition.tracks:
        track = MidiTrack()
        track.append(MetaMessage("track_name", name=track_events.name or track_events.track_id))
        program = _resolve_program(track_events.instrument, track_events.channel)
        if program is not None:
            track.append(Message("program_change", program=program, time=0, channel=track_events.channel))

        # 事件列表：(tick, kind) kind: 0=note_off, 1=note_on
        events: list[tuple[int, int, int, int]] = []
        for note in track_events.notes:
            start_tick = int(round(note.start_beat * tpb))
            end_tick = int(round((note.start_beat + note.duration_beats) * tpb))
            events.append((start_tick, 1, note.pitch, note.velocity))
            events.append((end_tick, 0, note.pitch, 0))

        events.sort(key=lambda e: (e[0], e[1]))
        last_tick = 0
        for tick, kind, pitch, velocity in events:
            delta = max(0, tick - last_tick)
            last_tick = tick
            if kind == 1:
                track.append(Message("note_on", note=pitch, velocity=velocity, time=delta, channel=track_events.channel))
            else:
                track.append(Message("note_off", note=pitch, velocity=velocity, time=delta, channel=track_events.channel))
        track.append(MetaMessage("end_of_track"))
        midi.tracks.append(track)

    midi.save(str(output))
    return output
