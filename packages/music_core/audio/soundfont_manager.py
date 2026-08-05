"""SoundFont 管理：扫描目录、稳定 id、默认选择。

扫描目录：
    - data/soundfonts/
    - assets/soundfonts/
    - 环境变量 SOUNDFONT_DIR
支持扩展名：.sf2 / .sf3 / .sfz
不因缺少音源而报错；不扫描/不提交真实音源文件。
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from packages.music_core.audio.soundfont_models import SoundFontInfo

SUPPORTED_EXTENSIONS = (".sf2", ".sf3", ".sfz")

_DEFAULT_SCAN_DIRS = ("data/soundfonts", "assets/soundfonts")

# 文件名关键词 → 风格 tag（轻量启发式）
_TAG_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("fluid", "general-midi"),
    ("orchestra", "orchestral"),
    ("string", "strings"),
    ("piano", "piano"),
    ("warm", "warm"),
    ("vintage", "vintage"),
    ("electric", "electric-guitar"),
    ("guitar", "guitar"),
    ("band", "band"),
    ("ethnic", "ethnic"),
    ("synth", "synth"),
    ("pad", "pad"),
)


def _scan_dirs() -> list[Path]:
    """收集需要扫描的目录（去重、忽略不存在目录）。"""
    dirs: list[Path] = [Path(name) for name in _DEFAULT_SCAN_DIRS]
    env_dir = os.getenv("SOUNDFONT_DIR", "").strip()
    if env_dir:
        dirs.append(Path(env_dir))
    seen: set[str] = set()
    result: list[Path] = []
    for directory in dirs:
        resolved = str(directory.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        if directory.exists() and directory.is_dir():
            result.append(directory)
    return result


def _stable_id(path: Path) -> str:
    """基于绝对路径生成稳定 id（同一路径多次扫描结果一致）。"""
    return hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()[:12]


def _tags_for(path: Path) -> list[str]:
    name = path.stem.lower()
    tags = [tag for keyword, tag in _TAG_KEYWORDS if keyword in name]
    return tags


def _info_from_path(path: Path) -> SoundFontInfo:
    return SoundFontInfo(
        id=_stable_id(path),
        name=path.stem,
        path=str(path),
        format=path.suffix.lstrip("."),
        size_bytes=path.stat().st_size,
        is_default=False,
        tags=_tags_for(path),
    )


def scan_soundfonts() -> list[SoundFontInfo]:
    """扫描所有支持目录，返回 SoundFontInfo 列表（无音源时返回空列表）。"""
    found: list[SoundFontInfo] = []
    for directory in _scan_dirs():
        for ext in SUPPORTED_EXTENSIONS:
            for path in sorted(directory.glob(f"*{ext}")):
                if path.is_file():
                    found.append(_info_from_path(path))
    return found


def soundfont_path_override() -> Path | None:
    """SOUNDFONT_PATH 显式指定的音源（存在才返回）。"""
    raw = os.getenv("SOUNDFONT_PATH", "").strip()
    if not raw:
        return None
    path = Path(raw)
    return path if path.exists() and path.is_file() else None


def resolve_default_soundfont() -> SoundFontInfo | None:
    """默认音源策略：DEFAULT_SOUNDFONT_ID > SOUNDFONT_PATH > 扫描到的第一个。"""
    fonts = scan_soundfonts()
    preferred_id = os.getenv("DEFAULT_SOUNDFONT_ID", "").strip()
    if preferred_id:
        for sf in fonts:
            if sf.id == preferred_id:
                return sf
    override = soundfont_path_override()
    if override is not None:
        return _info_from_path(override)
    return fonts[0] if fonts else None


def list_soundfonts() -> list[SoundFontInfo]:
    """返回全部音源并标记默认；SOUNDFONT_PATH 指向扫描目录外的音源时也会加入。"""
    fonts = scan_soundfonts()
    default = resolve_default_soundfont()
    if default is not None:
        matched = False
        for sf in fonts:
            if sf.id == default.id:
                sf.is_default = True
                matched = True
                break
        if not matched and default.path not in {sf.path for sf in fonts}:
            fonts.append(default.model_copy(update={"is_default": True}))
    return fonts


def get_soundfont(soundfont_id: str) -> SoundFontInfo | None:
    """按 id 查找音源；不存在返回 None。"""
    for sf in list_soundfonts():
        if sf.id == soundfont_id:
            return sf
    return None
