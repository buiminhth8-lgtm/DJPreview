"""MixEngine：默认混音、同步、应用与更新。"""

from __future__ import annotations

import copy
import logging

from packages.music_core.composer.events import CompositionResult, TrackEvents
from packages.music_core.instruments.registry import get_gm_program, is_drum_instrument
from packages.music_core.mix.mix_models import MixSpec, TrackMixSpec
from packages.music_core.midi.midi_constants import DRUM_CHANNEL
from services.api.schemas.music_spec import MusicSpec

logger = logging.getLogger(__name__)


def _pan_to_cc(pan: float) -> int:
    """pan -1..1 → CC10 值 0..127。"""
    return max(0, min(127, int(round((pan + 1.0) / 2.0 * 127))))


def _default_track_mix(track) -> TrackMixSpec:
    is_drum = track.role == "drums" or is_drum_instrument(track.instrument)
    program = None if is_drum else get_gm_program(track.instrument, default=0)
    return TrackMixSpec(
        track_id=track.id,
        role=track.role,
        program=program,
        instrument=track.instrument,
    )


def create_default_mix_spec(
    music_spec: MusicSpec,
    song_id: str | None = None,
    version_id: str | None = None,
) -> MixSpec:
    """根据 MusicSpec.tracks 自动创建默认 MixSpec。"""
    return MixSpec(
        version="0.1",
        song_id=song_id,
        version_id=version_id,
        master_volume=1.0,
        tracks=[_default_track_mix(t) for t in music_spec.tracks],
        notes=None,
    )


def sync_mix_spec_with_music_spec(mix_spec: MixSpec, music_spec: MusicSpec) -> MixSpec:
    """同步 MixSpec 与 MusicSpec：删除已不存在的轨道，为新增轨道补默认值。"""
    track_ids = {t.id for t in music_spec.tracks}
    tracks = [t for t in mix_spec.tracks if t.track_id in track_ids]
    existing = {t.track_id for t in tracks}
    for track in music_spec.tracks:
        if track.id not in existing:
            tracks.append(_default_track_mix(track))
    return mix_spec.model_copy(update={"tracks": tracks})


def update_track_mix(mix_spec: MixSpec, track_id: str, patch: dict) -> MixSpec:
    """合并更新某轨道的混音参数（不修改原对象）。"""
    tracks: list[TrackMixSpec] = []
    for t in mix_spec.tracks:
        if t.track_id == track_id:
            data = t.model_dump()
            for key, value in patch.items():
                if value is not None and key in data:
                    data[key] = value
            tracks.append(TrackMixSpec.model_validate(data))
        else:
            tracks.append(t)
    return mix_spec.model_copy(update={"tracks": tracks})


def _find_mix(track: TrackEvents, mix_spec: MixSpec) -> TrackMixSpec | None:
    for m in mix_spec.tracks:
        if m.track_id == track.track_id:
            return m
    for m in mix_spec.tracks:
        if m.role and m.role == track.role:
            return m
    return None


def apply_mix_to_composition(composition: CompositionResult, mix_spec: MixSpec) -> CompositionResult:
    """把 MixSpec 应用到 CompositionResult，返回深拷贝结果（不修改原对象）。

    - volume / velocity_scale / master_volume 缩放 velocity（1-127）
    - mute / enabled=false 不输出该轨道
    - solo 优先：任意轨道 solo 时只输出 solo 轨道
    - pan 写入 TrackEvents.pan（CC10 值）
    - 所有轨道被静音时保留 melody 或第一条可用轨道，并记录 warning
    """
    result = copy.deepcopy(composition)
    warnings: list[str] = []
    original_notes = {t.track_id: list(t.notes) for t in composition.tracks}

    has_solo = any(m.solo for m in mix_spec.tracks)
    for track in result.tracks:
        mix = _find_mix(track, mix_spec)
        if mix is None:
            continue
        if has_solo and not mix.solo:
            track.notes = []
            continue
        if not mix.enabled or mix.mute:
            track.notes = []
            continue
        scale = mix.volume * mix.velocity_scale * mix_spec.master_volume
        for note in track.notes:
            note.velocity = max(1, min(127, int(round(note.velocity * scale))))
        if track.channel != DRUM_CHANNEL:
            track.pan = _pan_to_cc(mix.pan)

    non_empty = [t for t in result.tracks if t.notes]
    if not non_empty:
        # 保留 melody 或第一条可用轨道，避免输出全空
        candidates = [t for t in result.tracks if t.role == "melody"] or result.tracks
        if candidates:
            kept = candidates[0]
            kept.notes = copy.deepcopy(original_notes.get(kept.track_id, []))
            mix = _find_mix(kept, mix_spec)
            if mix is not None:
                scale = max(0.1, mix.volume * mix.velocity_scale * mix_spec.master_volume)
                for note in kept.notes:
                    note.velocity = max(1, min(127, int(round(note.velocity * scale))))
                if kept.channel != DRUM_CHANNEL:
                    kept.pan = _pan_to_cc(mix.pan)
                warnings.append(
                    f"所有轨道均被静音/禁用，已保留 {kept.track_id} 轨道以保证输出非空"
                )

    result.warnings = warnings
    return result
