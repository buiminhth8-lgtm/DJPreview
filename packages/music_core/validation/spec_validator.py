"""MusicSpec 语义校验器：输出 errors / warnings 报告，并支持严格校验。"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field, ValidationError

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


# ---------- T10：统一 ValidationResult 语义校验 ----------


class ValidationIssue(BaseModel):
    """单条语义校验问题。"""

    code: str
    message: str
    path: str | None = None
    details: dict = Field(default_factory=dict)


class ValidationResult(BaseModel):
    """统一语义校验结果。"""

    valid: bool
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)


def validate_music_spec_semantics(music_spec: MusicSpec | dict) -> ValidationResult:
    """统一语义校验入口：收集所有 error/warning（不提前退出），返回 ValidationResult。"""
    if isinstance(music_spec, dict):
        try:
            music_spec = MusicSpec.model_validate(music_spec)
        except ValidationError as exc:
            return ValidationResult(
                valid=False,
                errors=[
                    ValidationIssue(
                        code="INVALID_MUSIC_SPEC_STRUCTURE",
                        message=f"MusicSpec 结构无效：{exc}",
                    )
                ],
            )

    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    if not music_spec.tracks:
        errors.append(ValidationIssue(code="EMPTY_TRACKS", message="tracks 不能为空", path="tracks"))
    if not music_spec.form:
        errors.append(ValidationIssue(code="EMPTY_FORM", message="form 不能为空", path="form"))
    if not music_spec.harmony:
        errors.append(ValidationIssue(code="EMPTY_HARMONY", message="harmony 不能为空", path="harmony"))

    form_ids = [s.id for s in music_spec.form]
    form_set = set(form_ids)
    duplicate_sections = sorted({sid for sid in form_ids if form_ids.count(sid) > 1})
    for sid in duplicate_sections:
        errors.append(
            ValidationIssue(
                code="DUPLICATE_SECTION_ID",
                message=f"section.id 重复：{sid}",
                path="form",
                details={"section_id": sid},
            )
        )

    total_bars = music_spec.length.bars
    ranges = [(s.id, s.start_bar, s.start_bar + s.bars - 1) for s in music_spec.form]
    for i in range(len(ranges)):
        for j in range(i + 1, len(ranges)):
            a, b = ranges[i], ranges[j]
            if not (a[2] < b[1] or b[2] < a[1]):
                errors.append(
                    ValidationIssue(
                        code="SECTION_OVERLAP",
                        message=f"段落 {a[0]} 与 {b[0]} 的小节范围重叠",
                        path="form",
                        details={"sections": [a[0], b[0]]},
                    )
                )
    for s in music_spec.form:
        end_bar = s.start_bar + s.bars - 1
        if s.start_bar < 1 or end_bar > total_bars:
            errors.append(
                ValidationIssue(
                    code="SECTION_OUT_OF_RANGE",
                    message=f"段落 {s.id} 超出整曲小节范围（length.bars={total_bars}）",
                    path=f"form.{s.id}",
                    details={"start_bar": s.start_bar, "end_bar": end_bar, "total_bars": total_bars},
                )
            )

    covered = set()
    for s in music_spec.form:
        covered.update(range(s.start_bar, s.start_bar + s.bars))
    if music_spec.form:
        uncovered = [b for b in range(1, total_bars + 1) if b not in covered]
        if uncovered:
            warnings.append(
                ValidationIssue(
                    code="SECTION_COVERAGE_GAP",
                    message=f"有 {len(uncovered)} 个小节未被任何段落覆盖",
                    path="form",
                    details={"uncovered_bars": uncovered[:20]},
                )
            )

    track_ids = [t.id for t in music_spec.tracks]
    duplicate_tracks = sorted({tid for tid in track_ids if track_ids.count(tid) > 1})
    for tid in duplicate_tracks:
        errors.append(
            ValidationIssue(
                code="DUPLICATE_TRACK_ID",
                message=f"track_id 重复：{tid}",
                path="tracks",
                details={"track_id": tid},
            )
        )
    for t in music_spec.tracks:
        if t.enabled_sections:
            missing = [sid for sid in t.enabled_sections if sid not in form_set]
            if missing:
                errors.append(
                    ValidationIssue(
                        code="UNKNOWN_ENABLED_SECTION",
                        message=f"轨道 {t.id} 的 enabled_sections 引用了不存在的段落：{missing}",
                        path=f"tracks.{t.id}",
                        details={"missing": missing},
                    )
                )

    for h in music_spec.harmony:
        if h.section not in form_set:
            errors.append(
                ValidationIssue(
                    code="UNKNOWN_HARMONY_SECTION",
                    message=f"harmony 引用了不存在的段落：{h.section}",
                    path="harmony",
                    details={"section": h.section},
                )
            )
        for chord in h.progression:
            if not is_valid_chord_symbol(chord):
                errors.append(
                    ValidationIssue(
                        code="INVALID_CHORD_SYMBOL",
                        message=f"和弦无法解析：{chord}",
                        path=f"harmony.{h.section}",
                        details={"chord": chord},
                    )
                )

    if not is_valid_note_name(music_spec.tonality.key):
        errors.append(
            ValidationIssue(
                code="INVALID_KEY",
                message=f"非法调性 key：{music_spec.tonality.key}",
                path="tonality.key",
                details={"key": music_spec.tonality.key},
            )
        )
    if not is_supported_mode(music_spec.tonality.mode):
        errors.append(
            ValidationIssue(
                code="INVALID_MODE",
                message=f"非法调式 mode：{music_spec.tonality.mode}",
                path="tonality.mode",
                details={"mode": music_spec.tonality.mode},
            )
        )

    if music_spec.meter.denominator not in (2, 4, 8, 16):
        errors.append(
            ValidationIssue(
                code="INVALID_METER_DENOMINATOR",
                message=f"非法拍号分母：{music_spec.meter.denominator}",
                path="meter.denominator",
                details={"denominator": music_spec.meter.denominator},
            )
        )

    return ValidationResult(valid=not errors, errors=errors, warnings=warnings)
