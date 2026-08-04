"""编曲质量检查：结构 / 轨道 / 音域 / 密度 / 和声 / 混音诊断。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from packages.music_core.analysis.midi_parser import ParsedMidi
from packages.music_core.composer.events import CompositionResult
from packages.music_core.theory.chords import parse_chord_symbol
from services.api.schemas.music_spec import MusicSpec


class QualityIssue(BaseModel):
    severity: str  # info / warning / error
    category: str
    message: str
    target: dict | None = None
    suggestion: str | None = None


class QualityReport(BaseModel):
    score: float = Field(ge=0, le=100)
    level: str
    issues: list[QualityIssue] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    summary: str


def _level(score: float) -> str:
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "good"
    if score >= 50:
        return "fair"
    return "poor"


def check_arrangement_quality(
    music_spec: MusicSpec,
    composition: CompositionResult | None = None,
    parsed_midi: ParsedMidi | None = None,
) -> QualityReport:
    """生成编曲质量报告（仅诊断，不影响生成）。"""
    issues: list[QualityIssue] = []
    suggestions: list[str] = []

    # ---- 结构检查 ----
    if not music_spec.form:
        issues.append(QualityIssue(severity="error", category="structure", message="曲式为空，没有任何 section", suggestion="至少添加一个 section"))
    else:
        total_bars = music_spec.length.bars
        covered = set()
        for section in music_spec.form:
            for bar in range(section.start_bar, section.start_bar + section.bars):
                if bar in covered:
                    issues.append(QualityIssue(severity="warning", category="structure", message=f"段落 {section.id} 与其他段落小节重叠", target={"section": section.id}))
                covered.add(bar)
        uncovered = [b for b in range(1, total_bars + 1) if b not in covered]
        if uncovered:
            issues.append(QualityIssue(severity="warning", category="structure", message=f"有 {len(uncovered)} 个小节未被任何段落覆盖", suggestion="检查 section 是否覆盖全曲"))
        if total_bars < 8:
            issues.append(QualityIssue(severity="info", category="structure", message="整曲过短（<8 小节）"))

    # ---- 轨道检查 ----
    if not music_spec.tracks:
        issues.append(QualityIssue(severity="error", category="mix", message="没有任何轨道", suggestion="添加至少一个旋律或和声轨道"))
    else:
        roles = {t.role for t in music_spec.tracks}
        if not ({"melody", "harmony"} & roles):
            issues.append(QualityIssue(severity="warning", category="mix", message="缺少 melody 或 harmony 轨道", suggestion="添加旋律或和声轨道"))
        ids = [t.id for t in music_spec.tracks]
        if len(ids) != len(set(ids)):
            issues.append(QualityIssue(severity="error", category="mix", message="存在重复 track_id", suggestion="确保每个 track_id 唯一"))
        if composition:
            for track in composition.tracks:
                if not track.notes:
                    issues.append(QualityIssue(severity="info", category="mix", message=f"轨道 {track.track_id} 为空", target={"track_id": track.track_id}))

    # ---- 音域检查 ----
    if parsed_midi:
        melody_track = None
        bass_track = None
        for track in parsed_midi.tracks:
            name = track.track_name or ""
            if "melody" in name or track.channel == 0:
                melody_track = track
            if "bass" in name:
                bass_track = track
        if melody_track and melody_track.min_pitch is not None:
            if melody_track.min_pitch < 55:
                issues.append(QualityIssue(severity="info", category="range", message="旋律音域偏低（最低音 <55）", suggestion="适当提高旋律音区"))
            if melody_track.max_pitch and melody_track.max_pitch > 88:
                issues.append(QualityIssue(severity="info", category="range", message="旋律音域偏高（最高音 >88）", suggestion="适当降低旋律音区"))
        if bass_track and bass_track.max_pitch and bass_track.max_pitch > 52:
            issues.append(QualityIssue(severity="warning", category="range", message="贝斯音区过高（>52）", suggestion="降低贝斯八度"))

    # ---- 密度检查 ----
    if parsed_midi and parsed_midi.total_bars > 0:
        total_notes = sum(t.note_count for t in parsed_midi.tracks)
        per_bar = total_notes / parsed_midi.total_bars
        if per_bar < 4:
            issues.append(QualityIssue(severity="info", category="density", message=f"音符密度过低（约 {per_bar:.1f} 音符/小节）", suggestion="适当增加旋律或伴奏音符"))
        if per_bar > 40:
            issues.append(QualityIssue(severity="warning", category="density", message=f"音符密度过高（约 {per_bar:.1f} 音符/小节）", suggestion="适当减少音符或加长时值"))

    # ---- 和声检查 ----
    if not music_spec.harmony:
        issues.append(QualityIssue(severity="warning", category="harmony", message="缺少 harmony 和弦进行", suggestion="为每个段落补充和弦进行"))
    else:
        harmony_sections = {h.section for h in music_spec.harmony}
        spec_sections = {s.id for s in music_spec.form}
        missing = spec_sections - harmony_sections
        if missing:
            issues.append(QualityIssue(severity="warning", category="harmony", message=f"以下段落缺少和弦进行：{sorted(missing)}", suggestion="补充 harmony 配置"))
        for h in music_spec.harmony:
            if not h.progression:
                issues.append(QualityIssue(severity="error", category="harmony", message=f"段落 {h.section} 的和弦进行为空", target={"section": h.section}))

    # ---- 混音检查 ----
    if music_spec.tracks:
        max_velocity = max(t.velocity for t in music_spec.tracks)
        if max_velocity > 120:
            issues.append(QualityIssue(severity="info", category="mix", message=f"存在力度过大的轨道（velocity={max_velocity}）", suggestion="适当降低该轨道力度"))
        avg_velocity = sum(t.velocity for t in music_spec.tracks) / len(music_spec.tracks)
        if avg_velocity < 50:
            issues.append(QualityIssue(severity="warning", category="mix", message="整体力度偏低", suggestion="提高各轨道 velocity"))

    severity_weight = {"error": 15, "warning": 8, "info": 2}
    score = max(0, 100 - sum(severity_weight.get(i.severity, 2) for i in issues))
    suggestions = list({i.suggestion for i in issues if i.suggestion})
    summary = f"共发现 {len(issues)} 个问题（{sum(1 for i in issues if i.severity == 'error')} error / {sum(1 for i in issues if i.severity == 'warning')} warning），评分 {score:.0f}/100"
    return QualityReport(score=score, level=_level(score), issues=issues, suggestions=suggestions, summary=summary)
