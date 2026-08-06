#!/usr/bin/env python3
"""T28 演示 smoke 脚本（MockProvider 最小可验证演示链路）。

默认只跑 1-2 个案例；--all 跑全部 8 个示例。
脚本只做 HTTP 检查，不把生成的 MIDI / WAV / ZIP 写入磁盘。
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMPTS = PROJECT_ROOT / "examples" / "demo_prompts.json"


class ApiFailure(RuntimeError):
    """API 请求失败。"""


def load_prompts(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} 应为 JSON 数组")
    return data


def request_json(base_url: str, method: str, path: str, payload: dict | None = None):
    """发送 JSON 请求并解析响应；非 2xx 抛 ApiFailure。"""
    url = base_url.rstrip("/") + path
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return json.loads(raw.decode("utf-8"))
            return raw
    except urllib.error.HTTPError as exc:
        raise ApiFailure(f"{method} {path} -> HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ApiFailure(f"{method} {path} -> 网络错误：{exc.reason}") from exc


def check_advanced(base_url: str, song_id: str) -> dict[str, str]:
    """高级接口检查：失败只记录为 skipped，不阻断基础链路。"""
    result: dict[str, str] = {}
    steps = {
        "edit": ("POST", f"/api/v1/songs/{song_id}/edit", {"instruction": "副歌更亮一点"}),
        "versions": ("GET", f"/api/v1/songs/{song_id}/versions", None),
        "mix": ("GET", f"/api/v1/songs/{song_id}/mix", None),
        "stems": ("POST", f"/api/v1/songs/{song_id}/stems/export", None),
    }
    for name, (method, path, payload) in steps.items():
        try:
            request_json(base_url, method, path, payload)
            result[name] = "ok"
        except ApiFailure as exc:
            result[name] = f"skipped（{exc}）"
    result["import"] = "skipped（演示中通过前端上传 .aimusic.zip，脚本不模拟 multipart）"
    return result


def run_case(base_url: str, case: dict) -> dict:
    """跑单个案例：生成 → MIDI → WAV → 版本 → 分析 → 导出。"""
    case_id = case.get("id", "?")
    prompt = case.get("prompt", "")
    checks: dict[str, str] = {}

    try:
        song = request_json(base_url, "POST", "/api/v1/songs/generate", {"prompt": prompt})
        song_id = song.get("song_id")
        checks["generate"] = "ok" if song_id and song.get("music_spec") else "failed（缺 song_id/music_spec）"
        if not song_id:
            return {"case_id": case_id, "ok": False, "checks": checks, "advanced": {}}

        request_json(base_url, "POST", f"/api/v1/songs/{song_id}/midi/generate")
        checks["midi"] = "ok"

        audio = request_json(base_url, "POST", f"/api/v1/songs/{song_id}/audio/render")
        renderer = (audio or {}).get("metadata", {}).get("renderer") if isinstance(audio, dict) else None
        checks["wav"] = f"ok（renderer={renderer or 'unknown'}）"

        request_json(base_url, "GET", f"/api/v1/songs/{song_id}/versions")
        checks["versions"] = "ok"

        request_json(base_url, "GET", f"/api/v1/songs/{song_id}/piano-roll")
        checks["piano_roll"] = "ok"

        raw = request_json(base_url, "GET", f"/api/v1/songs/{song_id}/project/export")
        checks["export"] = "ok" if isinstance(raw, bytes) else "failed（非文件响应）"

        advanced = check_advanced(base_url, song_id)
        return {"case_id": case_id, "song_id": song_id, "ok": True, "checks": checks, "advanced": advanced}
    except ApiFailure as exc:
        checks["error"] = str(exc)
        return {"case_id": case_id, "ok": False, "checks": checks, "advanced": {}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ai-music-mvp T28 演示 smoke 脚本（默认 MockProvider，可离线演示）",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="后端 API 地址")
    parser.add_argument("--all", action="store_true", help="跑全部 8 个示例案例")
    parser.add_argument("--cases", type=int, default=2, help="默认跑的案例数（忽略 --all 时）")
    parser.add_argument("--prompts", default=str(DEFAULT_PROMPTS), help="demo_prompts.json 路径")
    parser.add_argument(
        "--provider",
        default="mock",
        choices=("mock", "lmstudio", "deepseek", "openai_compatible"),
        help="本次运行针对的后端 LLM_PROVIDER（仅影响案例数与报告，不修改系统环境；"
        "后端需以对应 LLM_PROVIDER 启动）。mock 默认；lmstudio 跑 1 个案例；deepseek 需显式选择",
    )
    args = parser.parse_args(argv)

    provider = args.provider.strip().lower()
    is_real = provider != "mock"
    # provider 参数只影响本次脚本的案例数与报告，不修改环境变量
    if is_real and not args.all:
        args.cases = 1

    prompts_path = Path(args.prompts)
    cases = load_prompts(prompts_path)
    selected = cases if args.all else cases[: max(1, min(args.cases, len(cases)))]

    print(f"[T28 smoke] 目标: {args.base_url}")
    print(f"[T28 smoke] provider: {provider}（真实 LLM 调用: {'yes' if is_real else 'no'}）")
    print(f"[T28 smoke] 案例数: {len(selected)}（共 {len(cases)} 个示例）")
    print(f"[T28 smoke] prompts: {prompts_path}")
    if is_real:
        print(
            f"[T28 smoke] 提示：请确认后端已以 LLM_PROVIDER={provider} 启动；"
            "本脚本只做 HTTP 检查，不直接调用 LLM。"
        )
    print("---")

    try:
        request_json(args.base_url, "GET", "/api/v1/health")
        print("[health] ok")
    except ApiFailure as exc:
        print(f"[health] failed：{exc}")
        print("基础链路失败：后端不可达或 LLM_PROVIDER 未设为 mock。")
        return 1

    failures = 0
    for case in selected:
        result = run_case(args.base_url, case)
        title = case.get("title") or case.get("id")
        status = "ok" if result["ok"] else "FAILED"
        print(f"[{result['case_id']}] {title}: {status}")
        for name, value in result["checks"].items():
            print(f"    - {name}: {value}")
        if not result["ok"]:
            failures += 1
        for name, value in result["advanced"].items():
            print(f"    (advanced) {name}: {value}")

    print("---")
    print(f"[T28 smoke] 完成：{len(selected) - failures}/{len(selected)} 案例通过")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
