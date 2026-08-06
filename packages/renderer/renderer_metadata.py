"""渲染器状态判定与 metadata 构建（T39-A）。

统一把 renderer / quality / soundfont / warnings 映射为前端可读的 metadata。
不改变渲染核心逻辑，只描述实际使用的渲染器与音源状态。
"""

from __future__ import annotations

# 结构化警告代码
WARNING_FALLBACK_QUALITY = "FALLBACK_RENDERER_QUALITY"
WARNING_SOUNDFONT_NOT_SELECTED = "SOUNDFONT_NOT_SELECTED"
WARNING_RENDERER_UNKNOWN = "RENDERER_UNKNOWN"

# 音质分级
QUALITY_PREVIEW = "preview"
QUALITY_BASIC = "basic"
QUALITY_SOUNDFONT = "soundfont"
QUALITY_UNKNOWN = "unknown"

# 渲染器显示名
LABEL_FALLBACK = "Fallback Preview Renderer"
LABEL_FLUIDSYNTH = "FluidSynth"
LABEL_UNKNOWN = "Unknown"

FALLBACK_WARNING_MESSAGE = (
    "当前使用 fallback renderer，音色为简易预览级合成，bass、drums、pad 可能不真实。"
    "请选择 SoundFont 并重新渲染 WAV，以获得更接近真实乐器或高质量合成器的音色。"
)


def renderer_label(renderer: str | None) -> str:
    """渲染器 → 人类可读名称。"""
    if not renderer:
        return LABEL_UNKNOWN
    if renderer == "fallback":
        return LABEL_FALLBACK
    if renderer == "fluidsynth":
        return LABEL_FLUIDSYNTH
    return LABEL_UNKNOWN


def classify_quality(renderer: str | None, soundfont_name: str | None) -> str:
    """按 renderer + soundfont 判定音质分级。"""
    if not renderer:
        return QUALITY_UNKNOWN
    if renderer == "fallback":
        return QUALITY_PREVIEW
    if renderer == "fluidsynth":
        return QUALITY_SOUNDFONT if soundfont_name else QUALITY_BASIC
    return QUALITY_UNKNOWN


def build_renderer_metadata(
    *,
    renderer: str | None,
    soundfont_id: str | None = None,
    soundfont_name: str | None = None,
    soundfont_path: str | None = None,
) -> dict:
    """构建前端统一的 renderer metadata 字段（不覆盖既有 warning 列表）。"""
    quality = classify_quality(renderer, soundfont_name)
    warnings: list[dict[str, str]] = []
    if quality == QUALITY_PREVIEW:
        warnings.append({"code": WARNING_FALLBACK_QUALITY, "message": FALLBACK_WARNING_MESSAGE})
    elif quality == QUALITY_BASIC:
        warnings.append(
            {
                "code": WARNING_SOUNDFONT_NOT_SELECTED,
                "message": "当前使用 FluidSynth 但未指定 SoundFont，音色质量有限，建议选择 SoundFont 后重新渲染。",
            }
        )
    elif quality == QUALITY_UNKNOWN:
        warnings.append(
            {
                "code": WARNING_RENDERER_UNKNOWN,
                "message": "无法识别当前渲染器，音质信息未知。",
            }
        )
    return {
        "renderer_label": renderer_label(renderer),
        "quality": quality,
        "soundfont_id": soundfont_id,
        "soundfont_name": soundfont_name,
        "soundfont_path": soundfont_path,
        "renderer_warnings": warnings,
    }
