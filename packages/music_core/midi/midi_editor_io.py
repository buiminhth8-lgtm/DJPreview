"""MIDI Editor 读取适配（T34.1，只读）。

把当前工程 output.mid 解析为 MidiEditorDocument：
- canonical 时间 = integer MIDI tick（保留文件实际 PPQ）
- Track ID = MusicSpec.track.id（稳定；MIDI track_name 与之匹配）
- Note ID = deterministic（track + channel + pitch + start_tick + 出现序号），跨读取稳定

不实现写回 / 保存（T34.2）。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import mido

from packages.music_core.midi.midi_constants import DRUM_CHANNEL
from services.api.schemas.midi_editor import (
    MidiEditorDocument,
    MidiEditorNote,
    MidiEditorTrack,
)

# 同一 (channel, pitch) 同 start_tick 的连续 note 用序号区分
_SAME_POSITION_MAX = 16


def _track_id_for(track_name: str | None, spec_track_ids: set[str], fallback_index: int) -> str:
    """稳定 track id：优先 MusicSpec track.id（含 divisi 派生名前缀匹配）。

    - track_name == track.id → 直接用
    - track_name.startswith(track.id + "_") → 用该 track.id（divisi）
    - 无法匹配 → "ext_{fallback_index}"（external 轨道，按 MIDI 轨道索引稳定）
    """
    if track_name:
        if track_name in spec_track_ids:
            return track_name
        for tid in spec_track_ids:
            if track_name.startswith(f"{tid}_"):
                return tid
    return f"ext_{fallback_index}"


def _note_id(track_name: str | None, channel: int, pitch: int, start_tick: int, occurrence: int) -> str:
    """deterministic note id（跨读取稳定）。"""
    raw = f"{track_name or ''}|{channel}|{pitch}|{start_tick}|{occurrence}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _role_for_track_name(track_name: str | None, role_by_track_id: dict[str, str]) -> str | None:
    """按 track_name 推断 role（确定性）：track.id → role 映射，divisi 归主轨道 role。"""
    if not track_name:
        return None
    if track_name in role_by_track_id:
        return role_by_track_id[track_name]
    for tid, role in role_by_track_id.items():
        if track_name.startswith(f"{tid}_"):
            return role
    return None


def _instrument_for_track_name(track_name: str | None, instrument_by_track_id: dict[str, str]) -> str | None:
    if not track_name:
        return None
    if track_name in instrument_by_track_id:
        return instrument_by_track_id[track_name]
    for tid, instrument in instrument_by_track_id.items():
        if track_name.startswith(f"{tid}_"):
            return instrument
    return None


def build_midi_editor_document(
    midi_path: str | Path,
    *,
    song_id: str,
    version_id: str | None = None,
    spec_track_ids: set[str] | None = None,
    role_by_track_id: dict[str, str] | None = None,
    instrument_by_track_id: dict[str, str] | None = None,
    max_notes_per_track: int = 10000,
) -> MidiEditorDocument:
    """把 MIDI 解析为编辑器文档（只读）。

    - 保留文件实际 PPQ；不强制 480。
    - 同 pitch 同 channel 重叠 note 用 FIFO 队列配对（与现有 parser 一致）。
    - note_on velocity=0 视为 note_off。
    """
    midi = mido.MidiFile(str(midi_path))
    tpb = midi.ticks_per_beat or 480
    spec_track_ids = spec_track_ids or set()
    role_by_track_id = role_by_track_id or {}
    instrument_by_track_id = instrument_by_track_id or {}

    tempo = None
    time_signature = (4, 4)
    track_tempo: list[int | None] = []
    track_ts: list[tuple[int, int]] = []

    editor_tracks: list[MidiEditorTrack] = []
    total_beats = 0.0

    for track_index, mido_track in enumerate(midi.tracks):
        tick = 0
        track_name: str | None = None
        track_channel: int | None = None
        seen_program = False

        # (channel, pitch) -> FIFO of (start_tick, velocity)
        active: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
        raw_notes: list[dict] = []

        for msg in mido_track:
            tick += msg.time
            if msg.type == "set_tempo":
                tempo = msg.tempo
                track_tempo.append(msg.tempo)
            elif msg.type == "time_signature":
                time_signature = (msg.numerator, msg.denominator)
                track_ts.append((msg.numerator, msg.denominator))
            elif msg.type == "track_name":
                track_name = msg.name
            elif msg.type == "program_change":
                seen_program = True
            elif msg.type == "note_on" and msg.velocity > 0:
                active.setdefault((msg.channel, msg.note), []).append((tick, msg.velocity, msg.channel))
                if track_channel is None:
                    track_channel = msg.channel
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                pending = active.get((msg.channel, msg.note))
                if not pending:
                    continue
                start_tick, velocity, channel = pending.pop(0)
                duration_tick = max(1, tick - start_tick)
                raw_notes.append(
                    {
                        "pitch": msg.note,
                        "start_tick": start_tick,
                        "duration_tick": duration_tick,
                        "velocity": velocity,
                        "channel": channel,
                    }
                )
                if track_channel is None:
                    track_channel = channel

        if not raw_notes and track_name is None and not seen_program:
            continue  # 空 meta 轨（如仅 tempo 的 0 号轨）跳过

        # 稳定 track id
        track_id = _track_id_for(track_name, spec_track_ids, track_index)
        channel = track_channel if track_channel is not None else 0
        is_drum = channel == DRUM_CHANNEL

        notes_out: list[MidiEditorNote] = []
        position_counts: dict[tuple[int, int, int], int] = {}
        for note in raw_notes[:max_notes_per_track]:
            key = (note["channel"], note["pitch"], note["start_tick"])
            occurrence = position_counts.get(key, 0)
            position_counts[key] = occurrence + 1
            notes_out.append(
                MidiEditorNote(
                    id=_note_id(track_name, note["channel"], note["pitch"], note["start_tick"], occurrence),
                    pitch=note["pitch"],
                    start_tick=note["start_tick"],
                    duration_tick=note["duration_tick"],
                    velocity=note["velocity"],
                    channel=note["channel"],
                )
            )
            total_beats = max(total_beats, (note["start_tick"] + note["duration_tick"]) / tpb)

        editor_tracks.append(
            MidiEditorTrack(
                id=track_id,
                role=_role_for_track_name(track_name, role_by_track_id),
                name=track_name or track_id,
                channel=channel,
                instrument=_instrument_for_track_name(track_name, instrument_by_track_id),
                is_drum=is_drum,
                notes=notes_out,
            )
        )

    bpm = round(60_000_000 / tempo) if tempo else None
    return MidiEditorDocument(
        song_id=song_id,
        version_id=version_id,
        ppq=tpb,
        bpm=bpm,
        time_signature=time_signature,
        total_bars=round(total_beats / time_signature[0], 2) if time_signature[0] else 0.0,
        tracks=editor_tracks,
    )
