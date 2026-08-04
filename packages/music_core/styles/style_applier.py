"""StyleApplier：把风格模板应用到 MusicSpec（不覆盖用户明确指定内容）。"""

from __future__ import annotations

import logging

from packages.music_core.styles.style_models import StyleTemplateSpec
from packages.music_core.validation.spec_validator import validate_music_spec
from services.api.schemas.music_spec import (
    MusicSpec,
    TempoSpec,
    TonalitySpec,
    TrackSpec,
)

logger = logging.getLogger(__name__)

# tempo / mode 只在 strength 接近 1 时覆盖用户指定值
_STRONG_STRENGTH = 0.8


def _blend_tempo(current: int, target: int | None, strength: float) -> int:
    if target is None:
        return current
    return max(40, min(220, int(round(current + (target - current) * strength))))


def _apply_default_tracks(spec: MusicSpec, template: StyleTemplateSpec, strength: float) -> MusicSpec:
    existing_roles = {t.role for t in spec.tracks}
    for tpl in template.default_tracks:
        role = tpl.get("role", "harmony")
        instrument = tpl.get("instrument", "piano")
        if role in existing_roles:
            continue
        if strength < 0.5 and role not in ("melody", "harmony"):
            continue
        track_id = tpl.get("id") or f"{role}_{len(spec.tracks) + 1}"
        if any(t.id == track_id for t in spec.tracks):
            track_id = f"{role}_{len(spec.tracks) + 1}"
        spec.tracks.append(
            TrackSpec(
                id=track_id,
                role=role,
                instrument=instrument,
                pattern=tpl.get("pattern"),
                register=tpl.get("register"),
                velocity=int(tpl.get("velocity") or 78),
            )
        )
    return spec


def _ensure_pentatonic(spec: MusicSpec, template: StyleTemplateSpec) -> MusicSpec:
    if "chinese" in template.tags or "pentatonic" in template.tags:
        if spec.tonality.mode != "pentatonic":
            spec.tonality = TonalitySpec(
                key=spec.tonality.key or "C",
                mode="pentatonic",
                scale=spec.tonality.scale or "major_pentatonic",
            )
    return spec


def apply_style_template_to_music_spec(
    music_spec: MusicSpec,
    template: StyleTemplateSpec,
    strength: float = 0.7,
) -> MusicSpec:
    """应用风格模板。

    - strength∈[0,1]，越高影响越强
    - tempo / mode 只在 strength≥0.8（接近 1）时覆盖用户指定值；key 从不覆盖
    - 轨道/风格/能量等可随 strength 渐进增强
    """
    strength = max(0.0, min(1.0, strength))
    spec = music_spec.model_copy(deep=True)

    if template.default_tempo is not None and strength >= _STRONG_STRENGTH:
        new_bpm = _blend_tempo(spec.tempo.bpm, template.default_tempo, strength)
        if new_bpm != spec.tempo.bpm:
            feel = "slow" if new_bpm <= 80 else ("medium" if new_bpm <= 140 else "fast")
            spec.tempo = TempoSpec(bpm=new_bpm, feel=feel)

    if strength >= 0.9 and template.preferred_modes:
        if spec.tonality.mode not in template.preferred_modes:
            mode = template.preferred_modes[0]
            spec.tonality = TonalitySpec(
                key=spec.tonality.key or "C",
                mode=mode,
                scale=spec.tonality.scale,
            )
    _ensure_pentatonic(spec, template)

    spec = _apply_default_tracks(spec, template, strength)
    for tpl in template.default_tracks:
        for track in spec.tracks:
            if track.role == tpl.get("role") and tpl.get("pattern") and strength >= 0.5:
                if not track.pattern:
                    track.pattern = tpl["pattern"]

    for tag in template.tags:
        if tag not in spec.style:
            spec.style = [*spec.style, tag]
    for mood_tag in ("cinematic", "calm", "epic"):
        if mood_tag in " ".join(template.tags).lower() and mood_tag not in spec.mood:
            spec.mood = [*spec.mood, mood_tag]

    if template.arrangement_curve and strength >= 0.5:
        curve = template.arrangement_curve
        for section in spec.form:
            if section.id in curve and isinstance(curve[section.id], (int, float)):
                target = max(0.0, min(1.0, float(curve[section.id])))
                section.energy = round(section.energy + (target - section.energy) * strength, 3)

    return validate_music_spec(spec)
