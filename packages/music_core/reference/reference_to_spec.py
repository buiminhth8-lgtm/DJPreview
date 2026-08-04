"""基于参考 MIDI 高层特征生成 MusicSpec（不复制旋律与和弦进行）。"""

from __future__ import annotations

from packages.llm.mock_provider import MockProvider
from packages.music_core.reference.reference_models import ReferenceMidiAnalysis
from packages.music_core.validation.spec_validator import validate_music_spec
from services.api.schemas.music_spec import LengthSpec, MusicSpec, SectionSpec, TempoSpec, TrackSpec


def _rescale_form(spec: MusicSpec, total_bars: int) -> MusicSpec:
    """按比例重排曲式到新的总小节数。"""
    if not spec.form:
        return spec
    current_total = sum(s.bars for s in spec.form)
    if current_total <= 0:
        return spec
    new_form: list[SectionSpec] = []
    start = 1
    for section in spec.form:
        bars = max(1, int(round(section.bars / current_total * total_bars)))
        new_form.append(
            SectionSpec(
                id=section.id,
                name=section.name,
                start_bar=start,
                bars=bars,
                energy=section.energy,
            )
        )
        start += bars
    # 最后一段吸收舍入误差
    overflow = start - 1 - total_bars
    if overflow > 0:
        new_form[-1] = new_form[-1].model_copy(update={"bars": max(1, new_form[-1].bars - overflow)})
    elif overflow < 0:
        new_form[-1] = new_form[-1].model_copy(update={"bars": new_form[-1].bars - overflow})
    spec.form = new_form
    return spec


def build_music_spec_from_reference(
    prompt: str,
    reference: ReferenceMidiAnalysis,
    base_spec: MusicSpec | None = None,
) -> MusicSpec:
    """融合参考特征（tempo/长度/轨道/能量曲线/风格标签），不复制具体音符。"""
    if base_spec is None:
        base_spec = MockProvider().generate_music_spec(prompt)
    spec = base_spec.model_copy(deep=True)

    if reference.bpm:
        target_bpm = max(40, min(220, reference.bpm))
        spec.tempo = TempoSpec(
            bpm=target_bpm,
            feel="slow" if target_bpm <= 80 else ("medium" if target_bpm <= 140 else "fast"),
        )

    total_bars = max(8, min(256, int(round(reference.estimated_bars or 32))))
    spec.length = LengthSpec(bars=total_bars)
    spec = _rescale_form(spec, total_bars)

    # 轨道：按参考角色补齐
    existing_roles = {t.role for t in spec.tracks}
    for suggestion in reference.suggested_tracks:
        role = suggestion.get("role")
        if role and role not in existing_roles:
            instrument = suggestion.get("instrument", "piano")
            spec.tracks.append(
                TrackSpec(
                    id=f"{role}_{len(spec.tracks) + 1}",
                    role=role,
                    instrument=instrument,
                    velocity=80,
                )
            )
            existing_roles.add(role)

    # 风格标签（只加不删）
    for tag in reference.suggested_style_tags:
        if tag not in spec.style:
            spec.style = [*spec.style, tag]

    # 能量曲线：映射到段落
    if reference.energy_curve and spec.form:
        segments = sorted(reference.energy_curve, key=lambda x: x.get("segment_index", 0))
        for i, section in enumerate(spec.form):
            segment = segments[i % len(segments)] if segments else None
            if segment:
                section.energy = round(max(0.0, min(1.0, float(segment.get("energy", section.energy)))), 3)

    return validate_music_spec(spec)
