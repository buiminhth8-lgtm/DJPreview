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


def write_midi_editor_track(
    midi_path: str | Path,
    output_path: str | Path,
    *,
    track_id: str,
    notes: list[MidiEditorNote],
    spec_track_ids: set[str],
) -> Path:
    """写回：把 MIDI 中目标轨道 note 事件替换为编辑后的 notes，保留他轨/其余消息。

    - track 定位：track_name == track_id（或 divisi 前缀）→ 用该 MIDI 轨道；
      external（ext_{index}）→ 用索引。
    - 目标轨重建：只保留 track_name/program_change/CC10/CC11/CC7/end_of_track，
      删除其 note_on/note_off，写入新 notes（tick 直接写入，不再 round(beat*tpb)）。
    - 其他轨：原样保留全部 message。
    - 输出 PPQ 与输入一致。
    """
    midi = mido.MidiFile(str(midi_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    tpb = midi.ticks_per_beat or 480

    def _matches(target_name: str | None) -> bool:
        if not target_name:
            return False
        if target_name == track_id:
            return True
        # external track
        if track_id.startswith("ext_") and target_name == track_id:
            return True
        # divisi 派生：track_id 是主轨 id，匹配 {id}_ 前缀轨道
        if track_id in spec_track_ids and target_name.startswith(f"{track_id}_"):
            return True
        return False

    def _match_by_index(index: int) -> bool:
        return track_id.startswith("ext_") and index == int(track_id.split("_", 1)[1])

    new_midi = mido.MidiFile(ticks_per_beat=tpb)
    target_replaced = False

    for track_index, mido_track in enumerate(midi.tracks):
        is_target = False
        target_name = None
        # 先扫 track_name 判断是否目标轨
        for msg in mido_track:
            if msg.type == "track_name":
                target_name = msg.name
        if _matches(target_name) or _match_by_index(track_index):
            is_target = True

        if not is_target:
            new_midi.tracks.append(mido_track)
            continue

        # 重建目标轨
        new_track = mido.MidiTrack()
        for msg in mido_track:
            if msg.type in ("note_on", "note_off"):
                continue
            new_track.append(msg)
        # 写入新 notes（events: (tick, kind) 0=off 1=on）
        events: list[tuple[int, int, int, int]] = []
        for note in notes:
            events.append((note.start_tick, 1, note.pitch, note.velocity))
            events.append((note.start_tick + note.duration_tick, 0, note.pitch, 0))
        events.sort(key=lambda e: (e[0], -e[1]))
        last = 0
        for tick, kind, pitch, velocity in events:
            delta = max(0, tick - last)
            last = tick
            if kind == 1:
                new_track.append(mido.Message("note_on", note=pitch, velocity=velocity, time=delta, channel=channel_of(notes) or 0))
            else:
                new_track.append(mido.Message("note_off", note=pitch, velocity=0, time=delta, channel=channel_of(notes) or 0))
        # end_of_track 可能已从原轨道保留；确保存在
        if not any(getattr(m, "type", None) == "end_of_track" for m in new_track):
            new_track.append(mido.MetaMessage("end_of_track"))
        new_midi.tracks.append(new_track)
        target_replaced = True

    if not target_replaced:
        raise ValueError(f"MIDI 中找不到目标轨道：{track_id}")

    new_midi.save(str(output))
    return output


def channel_of(notes: list[MidiEditorNote]) -> int:
    return notes[0].channel if notes else 0
