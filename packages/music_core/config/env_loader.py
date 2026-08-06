"""多 LLM 环境配置文件按需加载。

在真正调用 DeepSeek 之前，可在以下模式之间按需切换：
    MockProvider          -> .mock.env
    LM Studio 本地服务     -> .lmstudio.env
    DeepSeek 线上服务      -> .deepseek.env

支持两种选择方式（可同时使用，LLM_ENV_FILE 优先）：
    LLM_ENV_PROFILE=mock|lmstudio|deepseek
    LLM_ENV_FILE=.custom.env

加载优先级（低 -> 高，系统环境变量最高，永不被文件覆盖）：
    1. .env                      通用默认配置
    2. profile env file          .mock.env / .lmstudio.env / .deepseek.env
    3. LLM_ENV_FILE 指定文件      如果设置，优先于 profile file
    4. 系统环境变量               最高优先级

规则：
    - 不覆盖已存在的系统环境变量（除非 override=True）。
    - 文件不存在时返回 warning，不崩溃；.env 缺失也不崩溃。
    - 未知 profile 抛清晰 ValueError。
    - 只负责加载配置，不创建任何 key；日志不输出 API Key 原文。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

logger = logging.getLogger(__name__)

PROFILE_FILES = {
    "mock": ".mock.env",
    "lmstudio": ".lmstudio.env",
    "deepseek": ".deepseek.env",
}

_SENSITIVE_SUFFIXES = ("KEY", "TOKEN", "SECRET", "PASSWORD", "AUTHORIZATION")


@dataclass
class EnvLoadInfo:
    """env 加载结果摘要（用于启动日志，不含任何密钥）。"""

    profile: str | None = None
    loaded_files: list[Path] = field(default_factory=list)
    missing_files: list[Path] = field(default_factory=list)
    explicit_env_file: str | None = None

    def summary(self) -> str:
        """一行安全摘要：只含 profile 与文件名，不含任何值。"""
        profile = self.profile or "default"
        loaded = ", ".join(p.name for p in self.loaded_files) or "<none>"
        parts = [f"Loaded env profile: {profile}", f"Loaded env files: {loaded}"]
        if self.missing_files:
            skipped = ", ".join(p.name for p in self.missing_files)
            parts.append(f"Skipped (not found): {skipped}")
        return "\n".join(parts)


def _read_env(path: Path) -> dict[str, str] | None:
    """读取 env 文件为 dict；文件不存在或为空返回 None。"""
    if not path.is_file():
        return None
    values = dotenv_values(str(path))
    return {k: v for k, v in values.items() if v is not None}


def _resolve_profile_file(profile: str, env_dir: Path) -> Path | None:
    """返回 profile 对应的 env 文件；未知 profile 返回 None（由调用方报错）。"""
    if profile in PROFILE_FILES:
        return env_dir / PROFILE_FILES[profile]
    # 通用兜底：.{profile}.env 存在即视为有效
    generic = env_dir / f".{profile}.env"
    return generic if generic.is_file() else None


def mask_value(value: str | None) -> str:
    """把敏感值打码用于展示；空值返回 <unset>。"""
    if not value:
        return "<unset>"
    if len(value) <= 8:
        return "*" * len(value)
    return value[:3] + "*" * (len(value) - 6) + value[-3:]


def is_sensitive_key(key: str) -> bool:
    """判断 env 键名是否属于敏感字段（KEY / TOKEN / SECRET 等）。"""
    upper = key.upper()
    return any(suffix in upper for suffix in _SENSITIVE_SUFFIXES)


def mask_env_value(key: str, value: str | None) -> str:
    """按键名决定是否打码（敏感键打码，其余返回原值）。"""
    if is_sensitive_key(key):
        return mask_value(value)
    return value if value is not None else "<unset>"


def load_env(
    *,
    profile: str | None = None,
    env_file: str | None = None,
    env_dir: str | Path | None = None,
    override: bool = False,
    log: bool = True,
) -> EnvLoadInfo:
    """按优先级加载 env 文件到 os.environ。

    参数：
        profile:  指定 profile（mock / lmstudio / deepseek）；缺省读 LLM_ENV_PROFILE。
        env_file: 指定自定义 env 文件（.custom.env）；缺省读 LLM_ENV_FILE。
        env_dir:  项目根目录（env 文件的基准目录）；缺省为当前工作目录。
        override: 是否覆盖已存在的系统环境变量；默认 False（系统变量最高优先级）。
        log:      是否输出 warning（文件缺失时）。
    """
    env_dir = Path(env_dir) if env_dir is not None else Path.cwd()
    system_env = dict(os.environ)

    # 1) 通用默认配置
    merged: dict[str, str] = {}
    loaded: list[Path] = []
    missing: list[Path] = []
    base_values = _read_env(env_dir / ".env")
    if base_values is not None:
        merged.update(base_values)
        loaded.append(env_dir / ".env")

    # 2) profile env file
    resolved_profile = profile
    if resolved_profile is None:
        resolved_profile = (
            os.environ.get("LLM_ENV_PROFILE")
            or (base_values or {}).get("LLM_ENV_PROFILE")
            or None
        )
    if resolved_profile:
        resolved_profile = str(resolved_profile).strip().lower()
        profile_file = _resolve_profile_file(resolved_profile, env_dir)
        if profile_file is None:
            raise ValueError(
                f"未知的 LLM_ENV_PROFILE：{resolved_profile!r}（支持：{sorted(PROFILE_FILES)}；"
                "或提供 .{name}.env 文件）"
            )
        profile_values = _read_env(profile_file)
        if profile_values is None:
            missing.append(profile_file)
        else:
            merged.update(profile_values)
            loaded.append(profile_file)

    # 3) LLM_ENV_FILE 指定文件（优先于 profile file）
    resolved_env_file = env_file
    if resolved_env_file is None:
        resolved_env_file = os.environ.get("LLM_ENV_FILE") or merged.get("LLM_ENV_FILE")
    if resolved_env_file:
        env_file_path = Path(resolved_env_file)
        if not env_file_path.is_absolute():
            env_file_path = env_dir / env_file_path
        env_file_values = _read_env(env_file_path)
        if env_file_values is None:
            missing.append(env_file_path)
        else:
            merged.update(env_file_values)
            loaded.append(env_file_path)

    # 4) 应用：系统环境变量最高优先级，默认不被文件覆盖
    for key, value in merged.items():
        if override or key not in system_env:
            os.environ[key] = value

    if log:
        for path in missing:
            logger.warning("env 文件不存在，已跳过：%s", path)

    return EnvLoadInfo(
        profile=resolved_profile,
        loaded_files=loaded,
        missing_files=missing,
        explicit_env_file=str(resolved_env_file) if resolved_env_file else None,
    )
