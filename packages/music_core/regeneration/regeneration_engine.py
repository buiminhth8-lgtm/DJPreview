"""Regeneration Engine：section / track / section_track / overall 局部重生成。"""

from __future__ import annotations

import logging

from packages.music_core.generation.cadence_engine import enhance_harmony_with_cadences, suggest_section_cadence
from packages.music_core.regeneration.regeneration_models import RegenerationRequest
from packages.music_core.validation.spec_validator import validate_music_spec
from services.api.schemas.music_spec import MusicSpec

logger = logging.getLogger(__name__)


def _direction(seed: int, seed_offset: int) -> int:
    return 1 if (seed + seed_offset) % 2 == 0 else -1


def regenerate_music_spec(
    current_spec: MusicSpec,
    request: RegenerationRequest,
) -> tuple[MusicSpec, dict]:
    """按 scope 局部重生成 MusicSpec；返回 (新 spec, 变更报告)。"""
    spec = current_spec.model_copy(deep=True)
    changes: list[dict] = []
    warnings: list[str] = []
    strength = max(0.0, min(1.0, request.variation_strength))
    direction = _direction(spec.seed, request.seed_offset)

    if request.scope in ("section", "section_track"):
        section_id = request.section_id or "chorus"
        target = next((s for s in spec.form if s.id == section_id), None)
        if target is None:
            raise ValueError(f"段落不存在：{section_id}")
        target.energy = round(max(0.0, min(1.0, target.energy + direction * strength * 0.15)), 3)
        changes.append({"scope": "section", "section_id": section_id, "field": "form.energy"})

        if not request.keep_harmony:
            cadence = suggest_section_cadence(
                section_id,
                spec.tonality.key,
                spec.tonality.mode,
                spec.style,
                target.energy,
            )
            for harmony in spec.harmony:
                if harmony.section == section_id:
                    harmony.progression = cadence
                    changes.append({"scope": "section", "section_id": section_id, "field": "harmony.progression"})

        if request.scope == "section_track" and request.track_id:
            track = next((t for t in spec.tracks if t.id == request.track_id), None)
            if track is None:
                raise ValueError(f"轨道不存在：{request.track_id}")
            if request.keep_melody and track.role == "melody":
                warnings.append("keep_melody=true，跳过 melody 轨道参数修改")
            else:
                track.velocity = max(1, min(127, int(track.velocity + direction * strength * 20)))
                if request.keep_rhythm and track.role == "drums":
                    warnings.append("keep_rhythm=true，跳过 drums 轨道参数修改")
                else:
                    changes.append({"scope": "section_track", "section_id": section_id, "track_id": track.id, "field": "track.velocity"})

    elif request.scope == "track":
        if not request.track_id:
            raise ValueError("track 级重生成需要 track_id")
        track = next((t for t in spec.tracks if t.id == request.track_id), None)
        if track is None:
            raise ValueError(f"轨道不存在：{request.track_id}")
        if request.keep_melody and track.role == "melody":
            warnings.append("keep_melody=true，跳过 melody 轨道参数修改")
        else:
            track.velocity = max(1, min(127, int(track.velocity + direction * strength * 20)))
            changes.append({"scope": "track", "track_id": track.id, "field": "track.velocity"})
            if track.role == "drums" and not request.keep_rhythm:
                track.pattern = "rock" if track.pattern in ("pop", "lo-fi") else "pop"
                changes.append({"scope": "track", "track_id": track.id, "field": "track.pattern"})

    elif request.scope == "overall":
        spec.seed = spec.seed + request.seed_offset
        changes.append({"scope": "overall", "field": "seed"})
        if not request.keep_harmony:
            spec = enhance_harmony_with_cadences(spec, strength)
            changes.append({"scope": "overall", "field": "harmony"})

    validate_music_spec(spec)
    report = {"changes": changes, "warnings": warnings}
    return spec, report
