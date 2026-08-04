"""MusicEditSpec 应用引擎：把修改协议应用到 MusicSpec（不修改原始对象）。"""

from __future__ import annotations

import logging

from packages.music_core.validation.spec_validator import validate_music_spec
from services.api.schemas.music_edit_spec import EditOperation, EditTarget, MusicEditSpec
from services.api.schemas.music_spec import MusicSpec, SectionSpec, TempoSpec, TonalitySpec, TrackSpec

logger = logging.getLogger(__name__)

_TEMPO_MIN = 40
_TEMPO_MAX = 220

# 全局字段操作：target.section 指定时跳过，保证“只修改副歌相关字段”
_GLOBAL_FIELD_OPS = {"tempo", "tonality", "chinese_style", "style", "mood"}
# 段落级操作
_SECTION_OPS = {"energy"}
# 轨道级操作
_TRACK_OPS = {"velocity", "add_instrument", "remove_instrument"}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _tempo_feel(bpm: int) -> str:
    if bpm <= 80:
        return "slow"
    if bpm <= 140:
        return "medium"
    return "fast"


def _guess_role(instrument: str) -> str:
    name = instrument.lower()
    if "bass" in name:
        return "bass"
    if "drum" in name:
        return "drums"
    if "string" in name or name == "pad" or "pad" in name:
        return "pad"
    return "harmony"


def apply_music_edit(music_spec: MusicSpec, edit_spec: MusicEditSpec) -> MusicSpec:
    """把 MusicEditSpec 应用到 MusicSpec，返回新的 MusicSpec。

    - 基于 model_copy(deep=True)，绝不修改原始对象
    - preserve 中列出的字段不会被动
    - target.section 指定时只允许段落级操作
    - 最终通过 validate_music_spec 保证结果合法
    """
    result = music_spec.model_copy(deep=True)
    preserve = set(edit_spec.preserve or [])
    target = edit_spec.target

    for op in edit_spec.operations:
        op_type = (op.type or "").strip().lower()
        try:
            if not op_type:
                continue
            if target.section and op_type in _GLOBAL_FIELD_OPS:
                logger.warning("操作 %s 为全局操作，target.section=%s 时跳过", op_type, target.section)
                continue
            if target.section and op_type not in _SECTION_OPS and op_type != "add_instrument":
                logger.warning("操作 %s 不适用于段落目标，跳过", op_type)
                continue
            result = _apply_operation(result, op, target, preserve)
        except Exception as exc:  # noqa: BLE001 - 单个操作失败不影响整体
            logger.warning("操作 %s 应用失败：%s", op_type, exc)

    return validate_music_spec(result)


def _apply_operation(spec: MusicSpec, op: EditOperation, target: EditTarget, preserve: set[str]) -> MusicSpec:
    op_type = (op.type or "").strip().lower()
    if op_type == "tempo":
        return _apply_tempo(spec, op, preserve)
    if op_type == "tonality":
        return _apply_tonality(spec, op, preserve)
    if op_type == "energy":
        return _apply_energy(spec, op, target, preserve)
    if op_type == "velocity":
        return _apply_velocity(spec, op, target, preserve)
    if op_type == "add_instrument":
        return _apply_add_instrument(spec, op, target, preserve)
    if op_type == "remove_instrument":
        return _apply_remove_instrument(spec, op, preserve)
    if op_type == "chinese_style":
        return _apply_chinese_style(spec, preserve)
    if op_type == "style":
        return _apply_tag(spec, op, "style", preserve)
    if op_type == "mood":
        return _apply_tag(spec, op, "mood", preserve)
    logger.warning("未知操作类型 %r，跳过", op.type)
    return spec


def _apply_tempo(spec: MusicSpec, op: EditOperation, preserve: set[str]) -> MusicSpec:
    if "tempo" in preserve:
        logger.warning("tempo 在 preserve 列表中，跳过")
        return spec
    current = spec.tempo.bpm
    if isinstance(op.value, (int, float)):
        new_bpm = int(_clamp(float(op.value), _TEMPO_MIN, _TEMPO_MAX))
    elif op.amount is not None:
        new_bpm = int(_clamp(current + op.amount, _TEMPO_MIN, _TEMPO_MAX))
    else:
        logger.warning("tempo 操作缺少 value/amount，跳过")
        return spec
    if new_bpm != current:
        spec.tempo = TempoSpec(bpm=new_bpm, feel=_tempo_feel(new_bpm))
    return spec


def _apply_tonality(spec: MusicSpec, op: EditOperation, preserve: set[str]) -> MusicSpec:
    if "tonality" in preserve:
        logger.warning("tonality 在 preserve 列表中，跳过")
        return spec
    if not op.value:
        logger.warning("tonality 操作缺少 value，跳过")
        return spec
    params = op.params or {}
    spec.tonality = TonalitySpec(
        key=str(op.value),
        mode=str(params.get("mode") or "major"),
        scale=params.get("scale"),
    )
    return spec


def _apply_energy(spec: MusicSpec, op: EditOperation, target: EditTarget, preserve: set[str]) -> MusicSpec:
    if "form" in preserve:
        logger.warning("form 在 preserve 列表中，跳过")
        return spec
    for section in spec.form:
        if target.section and section.id != target.section:
            continue
        if op.value is not None:
            new_energy = _clamp(float(op.value), 0.0, 1.0)
        elif op.amount is not None:
            new_energy = _clamp(section.energy + op.amount, 0.0, 1.0)
        else:
            continue
        section.energy = round(new_energy, 3)
    return spec


def _apply_velocity(spec: MusicSpec, op: EditOperation, target: EditTarget, preserve: set[str]) -> MusicSpec:
    if "tracks" in preserve:
        logger.warning("tracks 在 preserve 列表中，跳过")
        return spec
    for track in spec.tracks:
        if target.track and track.id != target.track:
            continue
        if op.value is not None:
            new_velocity = int(_clamp(float(op.value), 1, 127))
        elif op.amount is not None:
            new_velocity = int(_clamp(track.velocity + op.amount, 1, 127))
        else:
            continue
        track.velocity = new_velocity
    return spec


def _apply_add_instrument(spec: MusicSpec, op: EditOperation, target: EditTarget, preserve: set[str]) -> MusicSpec:
    if "tracks" in preserve:
        logger.warning("tracks 在 preserve 列表中，跳过")
        return spec
    params = op.params or {}
    instrument = str(op.value or params.get("instrument") or "").strip()
    if not instrument:
        logger.warning("add_instrument 缺少乐器名，跳过")
        return spec
    role = str(params.get("role") or _guess_role(instrument))
    track_id = str(params.get("id") or f"{role}_{len(spec.tracks) + 1}")
    if any(t.id == track_id for t in spec.tracks):
        logger.warning("轨道 %s 已存在，跳过", track_id)
        return spec
    enabled_sections = [target.section] if target.section else params.get("enabled_sections")
    velocity = int(_clamp(float(params.get("velocity") or 80), 1, 127))
    spec.tracks.append(
        TrackSpec(
            id=track_id,
            role=role,
            instrument=instrument,
            velocity=velocity,
            enabled_sections=enabled_sections,
        )
    )
    return spec


def _apply_remove_instrument(spec: MusicSpec, op: EditOperation, preserve: set[str]) -> MusicSpec:
    if "tracks" in preserve:
        logger.warning("tracks 在 preserve 列表中，跳过")
        return spec
    params = op.params or {}
    value = str(op.value or params.get("track") or params.get("instrument") or params.get("role") or "").strip().lower()
    if not value:
        logger.warning("remove_instrument 缺少目标，跳过")
        return spec
    remaining = [
        t
        for t in spec.tracks
        if not (
            t.id.lower() == value
            or t.instrument.lower() == value
            or t.role.lower() == value
        )
    ]
    if len(remaining) == len(spec.tracks):
        logger.warning("未找到要移除的轨道 %r", value)
        return spec
    if not remaining:
        logger.warning("不能移除最后一个轨道，跳过")
        return spec
    spec.tracks = remaining
    return spec


def _apply_chinese_style(spec: MusicSpec, preserve: set[str]) -> MusicSpec:
    if "tonality" in preserve:
        logger.warning("tonality 在 preserve 列表中，跳过")
        return spec
    spec.tonality = TonalitySpec(key=spec.tonality.key or "C", mode="pentatonic", scale="major_pentatonic")
    if "中国风" not in spec.style:
        spec.style = [*spec.style, "中国风"]
    return spec


def _apply_tag(spec: MusicSpec, op: EditOperation, field: str, preserve: set[str]) -> MusicSpec:
    if field in preserve:
        logger.warning("%s 在 preserve 列表中，跳过", field)
        return spec
    if not op.value:
        return spec
    tag = str(op.value)
    current = list(getattr(spec, field))
    if tag not in current:
        setattr(spec, field, [*current, tag])
    return spec
