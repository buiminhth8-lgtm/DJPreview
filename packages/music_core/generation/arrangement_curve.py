"""Arrangement Curve：段落能量/密度/轨道活跃度曲线。"""

from __future__ import annotations

from packages.music_core.styles.style_models import StyleTemplateSpec
from services.api.schemas.music_spec import MusicSpec


def _active_roles(section_id: str, energy: float) -> list[str]:
    if section_id == "intro":
        return ["harmony", "pad"]
    if section_id == "outro":
        return ["harmony", "pad", "melody"]
    roles = ["melody", "harmony", "bass"]
    if energy >= 0.6:
        roles.append("drums")
    if energy >= 0.75:
        roles.append("pad")
    return roles


def build_arrangement_curve(
    music_spec: MusicSpec,
    template: StyleTemplateSpec | None = None,
) -> dict:
    """输出逐段落 {energy, density, velocity_scale, active_roles}。"""
    template_curve = template.arrangement_curve if template else {}
    style_text = " ".join(music_spec.style + (template.tags if template else [])).lower()
    is_ambient = "ambient" in style_text
    is_battle = "battle" in style_text or "game" in style_text
    is_cinematic = "cinematic" in style_text

    sections = []
    for section in music_spec.form:
        energy = section.energy
        if section.id in template_curve and isinstance(template_curve[section.id], (int, float)):
            energy = float(template_curve[section.id])
        if is_ambient:
            energy = min(energy, 0.55)
        if is_battle:
            energy = max(energy, 0.6)
        if is_cinematic and section.id == "chorus":
            energy = max(energy, 0.85)

        density = 0.2 + energy * 0.55
        if is_ambient:
            density = min(density, 0.4)
        velocity_scale = round(0.7 + energy * 0.35, 3)
        sections.append(
            {
                "section_id": section.id,
                "energy": round(max(0.0, min(1.0, energy)), 3),
                "density": round(max(0.05, min(1.0, density)), 3),
                "velocity_scale": velocity_scale,
                "active_roles": _active_roles(section.id, energy),
            }
        )
    return {"sections": sections}


def apply_arrangement_curve_to_spec(music_spec: MusicSpec, curve: dict) -> MusicSpec:
    """把曲线中的 energy 写回 MusicSpec 段落。"""
    spec = music_spec.model_copy(deep=True)
    by_id = {item["section_id"]: item for item in curve.get("sections", [])}
    for section in spec.form:
        item = by_id.get(section.id)
        if item:
            section.energy = item["energy"]
    return spec
