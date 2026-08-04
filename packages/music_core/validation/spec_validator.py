"""MusicSpec 语义校验器。"""

from pydantic import ValidationError

from services.api.schemas.music_spec import MusicSpec


class MusicSpecValidationError(ValueError):
    """MusicSpec 校验失败时抛出。"""


def validate_music_spec(spec: MusicSpec | dict) -> MusicSpec:
    """校验 MusicSpec：结构合法 + 基本语义约束，返回规范化后的 MusicSpec。"""
    try:
        if isinstance(spec, dict):
            spec = MusicSpec.model_validate(spec)
    except ValidationError as exc:
        raise MusicSpecValidationError(f"MusicSpec 结构校验失败：{exc}") from exc

    if not spec.form:
        raise MusicSpecValidationError("MusicSpec 至少需要一个 section")
    if not spec.harmony:
        raise MusicSpecValidationError("MusicSpec 至少需要一个 harmony")
    if not spec.tracks:
        raise MusicSpecValidationError("MusicSpec 至少需要一个 track")

    total = spec.length.bars
    for section in spec.form:
        if section.start_bar < 1:
            raise MusicSpecValidationError(f"段落 {section.id!r} 的 start_bar 必须 >= 1")
        end_bar = section.start_bar + section.bars - 1
        if end_bar > total:
            raise MusicSpecValidationError(
                f"段落 {section.id!r} 结束于第 {end_bar} 小节，超出整曲范围（length.bars={total}）"
            )

    return spec
