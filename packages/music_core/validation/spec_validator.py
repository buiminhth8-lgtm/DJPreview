"""MusicSpec 语义校验器：输出 errors / warnings 报告，并支持严格校验。"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import ValidationError

from packages.music_core.theory.chords import is_valid_chord_symbol
from packages.music_core.theory.pitch import is_valid_note_name
from packages.music_core.theory.scales import is_supported_mode
from services.api.schemas.music_spec import MusicSpec


class MusicSpecValidationError(ValueError):
    """MusicSpec 校验失败时抛出。"""


@dataclass
class ValidationReport:
    """语义校验报告。"""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors


def _check_structure(report: ValidationReport, spec: MusicSpec) -> None:
    if not spec.form:
        report.errors.append("MusicSpec 至少需要一个 section")
    if not spec.harmony:
        report.errors.append("MusicSpec 至少需要一个 harmony")
    if not spec.tracks:
        report.errors.append("MusicSpec 至少需要一个 track")


def _check_sections(report: ValidationReport, spec: MusicSpec) -> None:
    if not spec.form:
        return
    ids = [s.id for s in spec.form]
    duplicates = sorted({sid for sid in ids if ids.count(sid) > 1})
    if duplicates:
        report.errors.append(f"section.id 重复：{duplicates}")

    # 重叠检查
    ranges = [(s.id, s.start_bar, s.start_bar + s.bars - 1) for s in spec.form]
    for i in range(len(ranges)):
        for j in range(i + 1, len(ranges)):
            a, b = ranges[i], ranges[j]
            if not (a[2] < b[1] or b[2] < a[1]):
                report.errors.append(f"段落 {a[0]} 与 {b[0]} 的小节范围重叠")

    total = spec.length.bars
    for section in spec.form:
        if section.start_bar < 1:
            report.errors.append(f"段落 {section.id!r} 的 start_bar 必须 >= 1")
        end_bar = section.start_bar + section.bars - 1
        if end_bar > total:
            report.errors.append(
                f"段落 {section.id!r} 结束于第 {end_bar} 小节，超出整曲范围（length.bars={total}）"
            )


def _check_tracks(report: ValidationReport, spec: MusicSpec) -> None:
    if not spec.tracks:
        return
    ids = [t.id for t in spec.tracks]
    duplicates = sorted({tid for tid in ids if ids.count(tid) > 1})
    if duplicates:
        report.errors.append(f"track_id 重复：{duplicates}")

    form_ids = {s.id for s in spec.form}
    for track in spec.tracks:
        if track.enabled_sections:
            missing = [sid for sid in track.enabled_sections if sid not in form_ids]
            if missing:
                report.errors.append(
                    f"轨道 {track.id!r} 的 enabled_sections 引用了不存在的段落：{missing}"
                )


def _check_harmony(report: ValidationReport, spec: MusicSpec) -> None:
    form_ids = {s.id for s in spec.form}
    for harmony in spec.harmony:
        if harmony.section not in form_ids:
            report.errors.append(f"harmony.section {harmony.section!r} 不存在于 form")
        if not harmony.progression:
            report.errors.append(f"段落 {harmony.section!r} 的和弦进行为空")
        for chord in harmony.progression:
            if not is_valid_chord_symbol(chord):
                report.errors.append(f"段落 {harmony.section!r} 的和弦 {chord!r} 无法解析")

    configured = {h.section for h in spec.harmony}
    for section in spec.form:
        if section.id not in configured:
            report.warnings.append(f"段落 {section.id!r} 缺少 harmony 配置（将使用默认进行）")


def _check_tonality(report: ValidationReport, spec: MusicSpec) -> None:
    if not is_valid_note_name(spec.tonality.key):
        report.errors.append(f"调性 key {spec.tonality.key!r} 不是合法音名")
    if not spec.tonality.mode:
        report.errors.append("tonality.mode 不能为空")
    elif not is_supported_mode(spec.tonality.mode):
        report.warnings.append(f"未知调式 {spec.tonality.mode!r}，生成时将回退为 major")


def check_music_spec(music_spec: MusicSpec | dict) -> ValidationReport:
    """语义校验，返回 errors / warnings 报告（不抛出）。"""
    if isinstance(music_spec, dict):
        music_spec = MusicSpec.model_validate(music_spec)
    report = ValidationReport()
    _check_structure(report, music_spec)
    _check_sections(report, music_spec)
    _check_tracks(report, music_spec)
    _check_harmony(report, music_spec)
    _check_tonality(report, music_spec)
    return report


def validate_music_spec(spec: MusicSpec | dict) -> MusicSpec:
    """严格校验：存在 errors 时抛出 MusicSpecValidationError，否则返回规范化 MusicSpec。"""
    try:
        if isinstance(spec, dict):
            spec = MusicSpec.model_validate(spec)
    except ValidationError as exc:
        raise MusicSpecValidationError(f"MusicSpec 结构校验失败：{exc}") from exc

    report = check_music_spec(spec)
    if report.errors:
        raise MusicSpecValidationError("MusicSpec 校验失败：" + "；".join(report.errors))
    return spec
