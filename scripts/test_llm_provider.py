#!/usr/bin/env python3
"""本地 LLM Provider 健康检查脚本。

用于在真正接入线上服务（DeepSeek）前，先验证本地 OpenAI-compatible 服务
（如 LM Studio）的完整链路：配置摘要 → /models → /chat/completions →
JSON 提取 → MusicSpec 校验。

用法示例：
    python scripts/test_llm_provider.py --help
    python scripts/test_llm_provider.py --provider mock
    python scripts/test_llm_provider.py --provider lmstudio
    python scripts/test_llm_provider.py --provider lmstudio \
        --base-url http://localhost:1234/v1 --model local-model
    python scripts/test_llm_provider.py --provider lmstudio \
        --generate-spec --song-prompt "生成一首雨夜电影感钢琴曲"

环境变量：LLM_PROVIDER / LMSTUDIO_* / OPENAI_COMPATIBLE_* / DEEPSEEK_*
脚本只在显式传入 --generate-midi / --render-audio 时写入文件（data/tmp_llm_provider_test/），
默认不生成任何 MIDI / WAV。
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
import warnings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# TrackSpec.register 与 BaseModel 属性重名仅为无害警告（与 pytest.ini 保持一致）
warnings.filterwarnings("ignore", message="Field name \"register\" in \"TrackSpec\".*", category=UserWarning)

from pydantic import BaseModel

from packages.llm.factory import get_llm_provider
from packages.llm.json_utils import extract_json_object
from packages.llm.structured_call import (
    LLMAPIError,
    LLMConfigurationError,
    LLMOutputError,
)
from services.api.schemas.music_spec import MusicSpec


class _PingResult(BaseModel):
    """最小 JSON 校验模型：验证 /chat/completions 返回合法 JSON。"""

    ok: bool = True
    echo: str | None = None


def _mask_key(value: str | None) -> str:
    if not value:
        return "<unset>"
    if len(value) <= 8:
        return "*" * len(value)
    return value[:3] + "*" * (len(value) - 6) + value[-3:]


def _run_mock(args: argparse.Namespace) -> int:
    """mock 模式：只做离线校验，不调用任何外部服务。"""
    print(f"[provider] mock（规则驱动，无网络调用）")
    if args.generate_spec:
        spec = get_llm_provider("mock").generate_music_spec(args.song_prompt)
        print(f"[music_spec] title={spec.title!r} tracks={len(spec.tracks)} bars={spec.length.bars}")
        print("[music_spec] 校验：ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="本地 LLM Provider 健康检查（默认 mock；真实服务可用 lmstudio / deepseek / openai_compatible）",
    )
    parser.add_argument(
        "--provider",
        default=os.getenv("LLM_PROVIDER", "") or "mock",
        help="provider 名称：mock / lmstudio / deepseek / openai_compatible（默认取 LLM_PROVIDER 或 mock）",
    )
    parser.add_argument("--base-url", default=None, help="OpenAI-compatible base url（如 http://localhost:1234/v1）")
    parser.add_argument("--model", default=None, help="模型名")
    parser.add_argument("--api-key", default=None, help="API key（本地服务可用占位值；缺省读取环境变量）")
    parser.add_argument("--timeout", type=float, default=None, help="HTTP 超时秒数")
    parser.add_argument("--prompt", default="只输出一个 JSON：{\"ok\": true}", help="最小 chat 提示词")
    parser.add_argument("--generate-spec", action="store_true", help="执行一次 generate_music_spec 全链路")
    parser.add_argument("--generate-midi", action="store_true", help="生成 MIDI 到临时数据目录")
    parser.add_argument("--render-audio", action="store_true", help="渲染 WAV 到临时数据目录（需 AUDIO_RENDERER 可用）")
    parser.add_argument("--song-prompt", default="生成一首雨夜电影感钢琴曲", help="generate_music_spec 用的歌曲提示词")
    args = parser.parse_args(argv)

    provider_name = args.provider.strip().lower()
    print(f"[provider] {provider_name}")

    if provider_name == "mock":
        return _run_mock(args)

    # 构造真实 provider（显式参数优先，未提供时读环境变量）
    kwargs: dict = {}
    if args.base_url is not None:
        kwargs["base_url"] = args.base_url
    if args.model is not None:
        kwargs["model"] = args.model
    if args.api_key is not None:
        kwargs["api_key"] = args.api_key
    if args.timeout is not None:
        kwargs["timeout"] = args.timeout
    try:
        provider = _construct_provider(provider_name, kwargs)
    except LLMConfigurationError as exc:
        print(f"[config] FAIL：{exc}")
        return 1
    except ValueError as exc:
        print(f"[provider] FAIL：{exc}")
        return 1

    print(f"[config] base_url={provider.base_url}")
    print(f"[config] model={provider.model or '<未设置>'}")
    print(f"[config] timeout={provider.timeout}")
    print(f"[config] api_key={_mask_key(provider.api_key)}")

    # 1) /models（服务支持才可用，失败不阻断）
    models: list[str] | None = None
    try:
        models = provider.fetch_models()
        print(f"[models] reachable，返回 {len(models)} 个模型：{', '.join(models[:10]) or '(空)'}")
    except LLMAPIError as exc:
        print(f"[models] skipped：{exc}")

    # 2) /chat/completions + JSON 提取（走统一结构化调用）
    try:
        result = provider.generate_structured(
            system_prompt="你是 JSON 助手，只输出 JSON。",
            user_prompt=args.prompt,
            response_model=_PingResult,
            task_name="ping",
        )
        print(f"[chat] ok -> {result.model_dump()}")
    except LLMAPIError as exc:
        print(f"[chat] FAIL：{exc}")
        return 1
    except LLMOutputError as exc:
        print(f"[chat] FAIL（JSON 解析失败）：{exc}")
        return 1

    # 3) 可选：完整生成 MusicSpec 链路
    if args.generate_spec:
        try:
            spec = provider.generate_music_spec(args.song_prompt)
            print(f"[music_spec] ok -> title={spec.title!r} tracks={len(spec.tracks)} bars={spec.length.bars} key={spec.tonality.key} mode={spec.tonality.mode}")
        except (LLMAPIError, LLMOutputError, ValueError) as exc:
            print(f"[music_spec] FAIL：{exc}")
            return 1

    # 4) 可选：MIDI / WAV 写入临时目录（data/tmp_llm_provider_test/）
    if args.generate_midi or args.render_audio:
        from packages.music_core.composer.music_composer import compose_music
        from packages.music_core.midi.midi_writer import write_midi
        from packages.music_core.validation.spec_validator import validate_music_spec
        from packages.renderer.factory import get_audio_renderer

        out_dir = PROJECT_ROOT / "data" / "tmp_llm_provider_test"
        out_dir.mkdir(parents=True, exist_ok=True)
        midi_path = out_dir / f"provider_check_{uuid.uuid4().hex[:8]}.mid"
        wav_path = out_dir / f"provider_check_{uuid.uuid4().hex[:8]}.wav"
        try:
            spec = validate_music_spec(provider.generate_music_spec(args.song_prompt))
            composition = compose_music(spec)
            write_midi(composition, midi_path)
            print(f"[midi] ok -> {midi_path}（{midi_path.stat().st_size} bytes）")
            if args.render_audio:
                result = get_audio_renderer().render_wav(
                    midi_path,
                    wav_path,
                    sample_rate=44100,
                    gain=0.6,
                    soundfont_path=None,
                )
                print(f"[wav] ok -> {wav_path}（{wav_path.stat().st_size} bytes，renderer={result.renderer}）")
        except Exception as exc:  # noqa: BLE001 - 脚本级诊断
            print(f"[generate] FAIL：{exc}")
            return 1

    print("---")
    print("[result] ALL OK")
    return 0


def _construct_provider(name: str, kwargs: dict):
    """按名称构造 provider 实例（显式参数优先，其余读环境变量）。"""
    if name == "lmstudio":
        from packages.llm.lmstudio_provider import LMStudioProvider

        return LMStudioProvider(**kwargs)
    if name == "deepseek":
        from packages.llm.deepseek_provider import DeepSeekProvider

        return DeepSeekProvider(**kwargs)
    if name in ("openai_compatible", "openai-compatible", "openai"):
        from packages.llm.openai_compatible_provider import OpenAICompatibleProvider

        return OpenAICompatibleProvider(**kwargs)
    raise ValueError(f"未知的 provider：{name!r}（支持：mock、lmstudio、deepseek、openai_compatible）")


if __name__ == "__main__":
    sys.exit(main())
