"""保守的编曲自动优化（规则式，不调用 LLM，不大改作品）。"""

from __future__ import annotations

import logging

from packages.music_core.analysis.quality_checker import QualityReport
from packages.music_core.validation.spec_validator import validate_music_spec
from services.api.schemas.music_spec import MusicSpec, SectionSpec, TonalitySpec, TrackSpec

logger = logging.getLogger(__name__)


def optimize_arrangement(
    music_spec: MusicSpec,
    quality_report: QualityReport | None = None,
) -> tuple[MusicSpec, dict]:
    """保守优化编曲：修复明显结构问题，返回 (新 MusicSpec, optimize_report)。"""
    spec = music_spec.model_copy(deep=True)
    changes: list[str] = []
    warnings: list[str] = []

    roles = {t.role for t in spec.tracks}
    ids = {t.id for t in spec.tracks}

    # 1. 缺少 melody → 添加
    if "melody" not in roles:
        track_id = "melody"
        if track_id in ids:
            track_id = "melody_opt"
        spec.tracks.append(
            TrackSpec(id=track_id, role="melody", instrument="lead_synth", pattern="legato", register="mid-high", velocity=95)
        )
        changes.append("添加 melody 轨道（lead_synth）")

    # 2. 缺少 harmony → 添加钢琴伴奏
    if "harmony" not in roles:
        track_id = "piano"
        if track_id in ids:
            track_id = "piano_opt"
        spec.tracks.append(
            TrackSpec(id=track_id, role="harmony", instrument="piano", pattern="comping", register="mid", velocity=78)
        )
        changes.append("添加 harmony 轨道（piano）")

    # 3. cinematic 风格缺 strings/pad → 添加
    style_text = " ".join(spec.style).lower()
    has_pad = any(t.role in ("pad", "strings") for t in spec.tracks)
    if any(k in style_text for k in ("cinematic", "ambient")) and not has_pad:
        track_id = "pad"
        if track_id in ids:
            track_id = "pad_opt"
        spec.tracks.append(
            TrackSpec(id=track_id, role="pad", instrument="strings", pattern="sustained", register="mid-low", velocity=70)
        )
        changes.append("为 cinematic/ambient 风格添加 strings pad 轨道")

    # 4. 中国风 / pentatonic 但 scale 未设置 → 设置 pentatonic
    if ("中国风" in spec.style or "chinese" in style_text) and spec.tonality.mode != "pentatonic":
        spec.tonality = TonalitySpec(key=spec.tonality.key or "C", mode="pentatonic", scale="major_pentatonic")
        changes.append("设置五声音阶（pentatonic）")

    # 5. chorus energy 低于 verse → 适当提高
    sections = {s.id: s for s in spec.form}
    if "chorus" in sections and "verse" in sections:
        verse_energy = sections["verse"].energy
        chorus_energy = sections["chorus"].energy
        if chorus_energy < verse_energy:
            sections["chorus"].energy = round(min(1.0, verse_energy + 0.1), 3)
            changes.append("提高 chorus energy（原低于 verse）")

    # 6. 所有轨道 velocity 过低 → 整体提高
    if spec.tracks and all(t.velocity < 60 for t in spec.tracks):
        for t in spec.tracks:
            t.velocity = min(127, t.velocity + 10)
        changes.append("整体提高轨道 velocity（原均低于 60）")

    # 7. 曲式为空 → 添加默认曲式
    if not spec.form:
        spec.form = [
            SectionSpec(id="intro", name="前奏", start_bar=1, bars=4, energy=0.2),
            SectionSpec(id="verse", name="主歌", start_bar=5, bars=8, energy=0.5),
            SectionSpec(id="chorus", name="副歌", start_bar=13, bars=16, energy=0.9),
            SectionSpec(id="outro", name="尾奏", start_bar=29, bars=4, energy=0.3),
        ]
        changes.append("添加默认曲式（intro/verse/chorus/outro）")

    validate_music_spec(spec)
    optimize_report = {"changes": changes, "warnings": warnings}
    return spec, optimize_report
