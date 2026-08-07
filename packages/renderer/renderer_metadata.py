"""渲染器状态判定与 metadata 构建（T39-A）。

统一把 renderer / quality / soundfont / warnings 映射为前端可读的 metadata。
不改变渲染核心逻辑，只描述实际使用的渲染器与音源状态。
"""

from __future__ import annotations

# 结构化警告代码
WARNING_FALLBACK_QUALITY = "FALLBACK_RENDERER_QUALITY"
WARNING_SOUNDFONT_NOT_SELECTED = "SOUNDFONT_NOT_SELECTED"
WARNING_RENDERER_UNKNOWN = "RENDERER_UNKNOWN"

# fallback 原因（结构化）
REASON_NO_SOUNDFONT_SELECTED = "no_soundfont_selected"
REASON_SOUNDFONT_FILE_MISSING = "soundfont_file_missing"
REASON_SOUNDFONT_NOT_FOUND = "soundfont_not_found"
REASON_FLUIDSYNTH_UNAVAILABLE = "fluidsynth_unavailable"
REASON_FLUIDSYNTH_RENDER_FAILED = "fluidsynth_render_failed"
REASON_RENDERER_NOT_CONFIGURED = "renderer_not_configured"
REASON_UNKNOWN = "unknown"

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

FALLBACK_REASON_MESSAGES: dict[str, str] = {
    REASON_NO_SOUNDFONT_SELECTED: "未选择 SoundFont，已回退到简易 renderer。请选择 SoundFont 后重新渲染。",
    REASON_SOUNDFONT_FILE_MISSING: "已选择 SoundFont 但文件缺失，已回退到简易 renderer。请重新下载或放置 SoundFont 后重新渲染。",
    REASON_SOUNDFONT_NOT_FOUND: "已选择 SoundFont 但本地找不到该音源，已回退到简易 renderer。请重新扫描并选择 SoundFont 后重新渲染。",
    REASON_FLUIDSYNTH_UNAVAILABLE: "已选择 SoundFont，但 FluidSynth 不可用，已回退到简易 renderer。请安装或配置 FluidSynth 后重新渲染。",
    REASON_FLUIDSYNTH_RENDER_FAILED: "FluidSynth 渲染失败，已回退到简易 renderer。请检查 SoundFont 与 FluidSynth 配置后重新渲染。",
    REASON_RENDERER_NOT_CONFIGURED: "渲染器未配置为使用 SoundFont，已回退到简易 renderer。请设置 AUDIO_RENDERER 后重新渲染。",
    REASON_UNKNOWN: "渲染器回退原因未知。",
}


def fallback_reason_message(reason: str | None) -> str | None:
    """fallback_reason → 人类可读说明。"""
    if not reason:
        return None
    return FALLBACK_REASON_MESSAGES.get(reason, reason)


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
    is_fallback: bool = False,
    fallback_reason: str | None = None,
) -> dict:
    """构建前端统一的 renderer metadata 字段（不覆盖既有 warning 列表）。"""
    quality = classify_quality(renderer, soundfont_name)
    warnings: list[dict[str, str]] = []
    if is_fallback:
        warnings.append(
            {
                "code": WARNING_FALLBACK_QUALITY,
                "message": FALLBACK_WARNING_MESSAGE,
            }
        )
        reason_message = fallback_reason_message(fallback_reason)
        if reason_message:
            warnings.append(
                {
                    "code": "FALLBACK_REASON",
                    "message": reason_message,
                }
            )
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
        "is_fallback": is_fallback,
        "fallback_reason": fallback_reason,
        "soundfont_id": soundfont_id,
        "soundfont_name": soundfont_name,
        "soundfont_path": soundfont_path,
        "renderer_warnings": warnings,
    }
