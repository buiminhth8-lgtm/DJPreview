"""MIDI 事件解析：MIDI 文件 → 音符级数据（beat 单位，不依赖 pretty_midi）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import mido

from packages.music_core.midi.midi_constants import DRUM_CHANNEL
from packages.music_core.theory.pitch import midi_to_note_name


@dataclass
class ParsedNote:
    track_index: int
    track_name: str | None
    channel: int
    pitch: int
    pitch_name: str
    start_beat: float
    duration_beats: float
    velocity: int
    is_drum: bool


@dataclass
class ParsedTrack:
    track_index: int
    track_name: str | None
    channel: int | None
    notes: list[ParsedNote] = field(default_factory=list)
    note_count: int = 0
    min_pitch: int | None = None
    max_pitch: int | None = None


@dataclass
class ParsedMidi:
    ticks_per_beat: int
    bpm: int | None
    total_beats: float
    total_bars: float
    tracks: list[ParsedTrack] = field(default_factory=list)


def _is_note_off(msg) -> bool:
    return msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0)


def parse_midi_to_notes(midi_path: str | Path) -> ParsedMidi:
    """解析 MIDI 文件，返回 ParsedMidi（beat 时间，多轨，鼓组 is_drum）。"""
    midi = mido.MidiFile(str(midi_path))
    tpb = midi.ticks_per_beat or 480
    tempo = None

    raw_notes: list[ParsedNote] = []
    for track_index, track in enumerate(midi.tracks):
        tick = 0
        track_name: str | None = None
        # 同一 (channel, note) 允许多个活动音符；用 list 保存并按 FIFO 配对，
        # 避免后一个 note_on 覆盖前一个导致同音重叠音符丢失。
        active: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
        for msg in track:
            tick += msg.time
            if msg.type == "set_tempo":
                tempo = msg.tempo
            elif msg.type == "track_name":
                track_name = msg.name
            elif msg.type == "note_on" and msg.velocity > 0:
                active.setdefault((msg.channel, msg.note), []).append(
                    (tick, msg.velocity, msg.channel)
                )
            elif _is_note_off(msg):
                pending = active.get((msg.channel, msg.note))
                if not pending:
                    # 未配对 note_off：忽略，不崩溃
                    continue
                start_tick, velocity, channel = pending.pop(0)  # FIFO
                raw_notes.append(
                    ParsedNote(
                        track_index=track_index,
                        track_name=track_name,
                        channel=channel,
                        pitch=msg.note,
                        pitch_name=midi_to_note_name(msg.note),
                        start_beat=round(start_tick / tpb, 4),
                        duration_beats=round(max(0.05, (tick - start_tick) / tpb), 4),
                        velocity=velocity,
                        is_drum=(channel == DRUM_CHANNEL),
                    )
                )

    bpm = round(60_000_000 / tempo) if tempo else None
    tracks: list[ParsedTrack] = []
    for track_index, track in enumerate(midi.tracks):
        notes = [n for n in raw_notes if n.track_index == track_index]
        if not notes:
            continue
        pitches = [n.pitch for n in notes]
        name = next((n.track_name for n in notes if n.track_name), None)
        channel = notes[0].channel
        tracks.append(
            ParsedTrack(
                track_index=track_index,
                track_name=name,
                channel=channel,
                notes=notes,
                note_count=len(notes),
                min_pitch=min(pitches),
                max_pitch=max(pitches),
            )
        )

    total_beats = round(max((n.start_beat + n.duration_beats for n in raw_notes), default=0.0), 4)
    beats_per_bar = 4
    total_bars = round(total_beats / beats_per_bar, 2)
    return ParsedMidi(
        ticks_per_beat=tpb,
        bpm=bpm,
        total_beats=total_beats,
        total_bars=total_bars,
        tracks=tracks,
    )
