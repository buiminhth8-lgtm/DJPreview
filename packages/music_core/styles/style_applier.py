"""StyleApplier：把风格模板应用到 MusicSpec（不覆盖用户明确指定内容）。"""

from __future__ import annotations

import logging
import zlib

from packages.music_core.styles.style_models import StyleTemplateSpec
from packages.music_core.styles.style_tags import normalize_style_tags
from packages.music_core.validation.spec_validator import validate_music_spec
from services.api.schemas.music_spec import (
    HarmonySectionSpec,
    MusicSpec,
    TempoSpec,
    TonalitySpec,
    TrackSpec,
)

logger = logging.getLogger(__name__)

# tempo / mode 只在 strength 接近 1 时覆盖用户指定值
_STRONG_STRENGTH = 0.8

# template pattern → 轨道可识别 pattern 的归一化映射
_PATTERN_ALIASES = {
    "lofi": "lofi_swing",
    "lo-fi": "lofi_swing",
    "lo_fi": "lofi_swing",
    "four_on_floor": "four_on_floor",
    "electronic": "four_on_floor",
    "rock": "rock_backbeat",
    "game": "battle_drive",
    "battle": "battle_drive",
    "cinematic": "cinematic_taiko",
    "chinese": "cinematic_taiko",
    "ambient": "ambient_minimal",
    "meditation": "ambient_minimal",
    "funk": "funk_groove",
    "roots": "root_fifth_drive",
    "root_fifth": "root_fifth_drive",
    "laidback": "laidback_groove",
    "octaves": "driving_octaves",
    "driving": "driving_octaves",
}


def _canonical_pattern(pattern: str | None) -> str | None:
    if not pattern:
        return None
    return _PATTERN_ALIASES.get(pattern.strip().lower(), pattern.strip().lower())


def _derived_seed(original_seed: int, template_id: str | None, strength: float) -> int:
    """派生可复现 seed：同 template + strength 稳定，不同 template 不同。"""
    if not template_id:
        return original_seed
    digest = zlib.crc32(f"{original_seed}:{template_id}:{round(strength, 3)}".encode("utf-8"))
    return original_seed + digest


def _blend_tempo(current: int, target: int | None, strength: float) -> int:
    if target is None:
        return current
    return max(40, min(220, int(round(current + (target - current) * strength))))


def _apply_default_tracks(spec: MusicSpec, template: StyleTemplateSpec, strength: float) -> MusicSpec:
    """应用模板轨道：strength≥0.5 时覆盖同 role 轨道的核心字段，否则仅补充缺失轨道。"""
    existing_roles = {t.role for t in spec.tracks}
    for tpl in template.default_tracks:
        role = tpl.get("role", "harmony")
        instrument = tpl.get("instrument", "piano")
        pattern = _canonical_pattern(tpl.get("pattern"))
        if role in existing_roles:
            # 已有轨道：strength≥0.5 时覆盖核心字段（保留 track id / enabled_sections 语义）
            if strength < 0.5:
                continue
            for track in spec.tracks:
                if track.role != role:
                    continue
                track.instrument = instrument
                if pattern:
                    track.pattern = pattern
                if tpl.get("register"):
                    track.register = tpl["register"]
                if tpl.get("velocity"):
                    track.velocity = int(tpl["velocity"])
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
                pattern=pattern,
                register=tpl.get("register"),
                velocity=int(tpl.get("velocity") or 78),
            )
        )
    return spec


def _apply_harmony_presets(spec: MusicSpec, template: StyleTemplateSpec, strength: float) -> MusicSpec:
    """把模板 harmony_presets 写入 MusicSpec.harmony（section-aware，保持 key/mode）。"""
    if not template.harmony_presets or strength < 0.5:
        return spec
    preset = template.harmony_presets[0]
    preset_by_section = {
        h.section: list(h.progression) for h in spec.harmony
    }
    new_harmony: list[HarmonySectionSpec] = []
    for section in spec.form:
        bars = max(1, section.bars)
        base = preset_by_section.get(section.id)
        if base and len(base) >= 2 and strength < 0.6:
            # 弱强度保守：保留已有进行
            progression = list(base)
        else:
            # 模板进行按段落长度循环铺满，保证和弦多样且可被 parser 解析
            progression = [preset[i % len(preset)] for i in range(bars)]
        new_harmony.append(
            HarmonySectionSpec(section=section.id, progression=progression)
        )
    spec.harmony = new_harmony
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
    spec = _apply_harmony_presets(spec, template, strength)

    # style / mood 标签合并
    normalized = normalize_style_tags([*spec.style, template.id, *template.tags])
    for canonical in sorted(normalized):
        if canonical not in spec.style:
            spec.style = [*spec.style, canonical]

    mood_map = {"game": "epic", "cinematic": "cinematic", "ambient": "calm", "meditation": "calm"}
    for canonical in normalized:
        if canonical in mood_map:
            mood = mood_map[canonical]
            if mood not in spec.mood:
                spec.mood = [*spec.mood, mood]

    # 模板参与 seed 派生：同 prompt + 不同 template 生成不同旋律，仍可复现
    spec.seed = _derived_seed(spec.seed, template.id, strength)

    if template.arrangement_curve and strength >= 0.5:
        curve = template.arrangement_curve
        for section in spec.form:
            if section.id in curve and isinstance(curve[section.id], (int, float)):
                target = max(0.0, min(1.0, float(curve[section.id])))
                section.energy = round(section.energy + (target - section.energy) * strength, 3)

    return validate_music_spec(spec)
