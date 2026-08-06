#!/usr/bin/env python3
"""在指定 LLM env profile 下运行命令（按需加载 .mock.env / .lmstudio.env / .deepseek.env）。

用法示例：
    python scripts/run_with_env.py --profile mock -- python -m pytest tests/test_generate_song_api.py -q
    python scripts/run_with_env.py --profile lmstudio -- python scripts/test_llm_provider.py --generate-spec
    python scripts/run_with_env.py --profile deepseek -- python scripts/test_llm_provider.py --generate-spec
    python scripts/run_with_env.py --profile lmstudio --print-env   # 只打印加载后的配置（敏感值打码）

说明：
    - 本脚本把 profile env 文件加载进进程环境，再透传给子命令（subprocess 继承 os.environ）。
    - 系统环境变量优先级最高，不会被文件覆盖。
    - 不提交任何真实 env 文件；API Key 打印时只显示掩码。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.music_core.config.env_loader import load_env, mask_env_value  # noqa: E402

_RELEVANT_KEYS = (
    "LLM_PROVIDER",
    "LLM_ENV_PROFILE",
    "LLM_ENV_FILE",
    "LMSTUDIO_BASE_URL",
    "LMSTUDIO_API_KEY",
    "LMSTUDIO_MODEL",
    "LMSTUDIO_TIMEOUT_SECONDS",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_MODEL",
    "DEEPSEEK_TIMEOUT_SECONDS",
    "OPENAI_COMPATIBLE_BASE_URL",
    "OPENAI_COMPATIBLE_API_KEY",
    "OPENAI_COMPATIBLE_MODEL",
    "OPENAI_COMPATIBLE_TIMEOUT_SECONDS",
    "AUDIO_RENDERER",
)


def _print_env(profile: str | None) -> None:
    print("--- 加载后的环境（敏感值已打码）---")
    for key in _RELEVANT_KEYS:
        value = os.environ.get(key)
        if value is None:
            continue
        print(f"{key}={mask_env_value(key, value)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="在指定 LLM env profile 下运行命令（按需加载 .mock.env / .lmstudio.env / .deepseek.env）",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="LLM env profile：mock / lmstudio / deepseek（缺省读 LLM_ENV_PROFILE）",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="自定义 env 文件（优先于 profile file；缺省读 LLM_ENV_FILE）",
    )
    parser.add_argument(
        "--print-env",
        action="store_true",
        help="只打印加载后的环境（敏感值打码），不执行命令",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="要执行的命令，前面加 --")
    args = parser.parse_args(argv)

    info = load_env(profile=args.profile, env_file=args.env_file, env_dir=PROJECT_ROOT)
    print(info.summary())

    if args.print_env:
        _print_env(info.profile)
        return 0

    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("[run_with_env] 未提供命令。示例：--profile mock -- python -m pytest tests/ -q")
        return 0

    print(f"[run_with_env] 执行: {' '.join(command)}")
    proc = subprocess.run(command, cwd=str(PROJECT_ROOT), env=os.environ)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
