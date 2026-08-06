"""MusicSpec 规范化：在语义校验 / MIDI 生成前统一修正 LLM 输出。

当前能力：轨道乐器名归一化（LLM 自然语言乐器别名 → 项目 canonical instrument id）。

流程位置：
    LLM raw JSON → JSON parse/repair → Pydantic MusicSpec
    → normalize_music_spec()（本模块）
    → semantic validation → create project → MIDI
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from packages.music_core.instruments.registry import normalize_instrument_name
from services.api.schemas.music_spec import MusicSpec

logger = logging.getLogger(__name__)


@dataclass
class InstrumentNormalization:
    """单条乐器归一化记录（供日志与 API debug 使用）。"""

    track_id: str
    role: str | None = None
    original: str | None = None
    normalized: str | None = None
    changed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "role": self.role,
            "from": self.original,
            "to": self.normalized,
            "changed": self.changed,
        }


def normalize_track_instruments(spec: MusicSpec) -> list[InstrumentNormalization]:
    """遍历 spec.tracks，把 instrument 统一归一化为 canonical id。

    保留 track 的 id / role / pattern / register / velocity / enabled_sections。
    返回归一化记录列表（含是否发生变更）。
    """
    records: list[InstrumentNormalization] = []
    for track in spec.tracks:
        instrument = track.instrument
        normalized = normalize_instrument_name(instrument, role=track.role)
        changed = normalized != instrument
        if changed and normalized:
            track.instrument = normalized
        records.append(
            InstrumentNormalization(
                track_id=track.id,
                role=track.role,
                original=instrument,
                normalized=track.instrument,
                changed=changed,
            )
        )
        if changed:
            log_stage_note(track.id, instrument, normalized)
    return records


def log_stage_note(track_id: str, original: str, normalized: str) -> None:
    """记录 instrument.normalized 阶段日志。"""
    from packages.llm.trace import get_request_id

    request_id = get_request_id()
    prefix = f"[request_id={request_id}]" if request_id else "[request_id=-]"
    logger.info(
        "%s instrument.normalized track_id=%s from=%s to=%s",
        prefix,
        track_id,
        original,
        normalized,
    )


def normalize_music_spec(spec: MusicSpec) -> tuple[MusicSpec, list[InstrumentNormalization]]:
    """规范化 MusicSpec（当前仅乐器名），返回 (spec, normalization_records)。"""
    records = normalize_track_instruments(spec)
    return spec, records
